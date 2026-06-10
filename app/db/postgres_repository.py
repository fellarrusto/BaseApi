import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

import asyncpg

from app.db.base_repository import BaseRepository

# Mongo-style operators supported in filters
_OPERATORS = {"$gt": ">", "$gte": ">=", "$lt": "<", "$lte": "<=", "$ne": "<>"}

class PostgresRepository(BaseRepository):
    """
    Document-style repository on PostgreSQL.

    Reference example: NOT wired into the app. To enable it, follow the
    "Switching to PostgreSQL" section in CLAUDE.md (requires asyncpg).

    Each collection maps to a table `(id TEXT PRIMARY KEY, data JSONB)`,
    created automatically on first use. Filters support equality and the
    Mongo-style operators $gt, $gte, $lt, $lte, $ne, $in. Values are
    compared as text, so range filters work on ISO-formatted dates.
    """

    def __init__(self, pool: asyncpg.Pool, table_name: str):
        self.pool = pool
        self.table = table_name
        self._table_ready = False

    async def _ensure_table(self) -> None:
        if self._table_ready:
            return
        async with self.pool.acquire() as conn:
            await conn.execute(
                f'CREATE TABLE IF NOT EXISTS "{self.table}" '
                "(id TEXT PRIMARY KEY, data JSONB NOT NULL)"
            )
        self._table_ready = True

    def _column(self, key: str) -> str:
        return "id" if key == "_id" else f"data->>'{key}'"

    def _build_where(self, filters: Dict[str, Any]) -> Tuple[str, List[Any]]:
        clauses: List[str] = []
        params: List[Any] = []
        for key, value in filters.items():
            column = self._column(key)
            if isinstance(value, dict):
                for op, op_value in value.items():
                    if op == "$in":
                        params.append([str(v) for v in op_value])
                        clauses.append(f"{column} = ANY(${len(params)})")
                    elif op in _OPERATORS:
                        params.append(self._to_text(op_value))
                        clauses.append(f"{column} {_OPERATORS[op]} ${len(params)}")
                    else:
                        raise ValueError(f"Unsupported filter operator: {op}")
            else:
                params.append(self._to_text(value))
                clauses.append(f"{column} = ${len(params)}")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return where, params

    @staticmethod
    def _to_text(value: Any) -> str:
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    @staticmethod
    def _row_to_doc(row: asyncpg.Record) -> Dict[str, Any]:
        doc = json.loads(row["data"])
        doc["_id"] = row["id"]
        return doc

    async def find_one(self, id: str) -> Optional[Dict[str, Any]]:
        await self._ensure_table()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                f'SELECT id, data FROM "{self.table}" WHERE id = $1', id
            )
        return self._row_to_doc(row) if row else None

    async def find_one_by(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        results = await self.find_many(filters, limit=1)
        return results[0] if results else None

    async def find_many(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        skip: int = 0,
        sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        await self._ensure_table()
        where, params = self._build_where(filters)

        order = ""
        if sort:
            parts = [
                f"{self._column(key)} {'ASC' if direction >= 0 else 'DESC'}"
                for key, direction in sort
            ]
            order = " ORDER BY " + ", ".join(parts)

        params.extend([skip, limit])
        query = (
            f'SELECT id, data FROM "{self.table}"{where}{order} '
            f"OFFSET ${len(params) - 1} LIMIT ${len(params)}"
        )
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [self._row_to_doc(row) for row in rows]

    async def count(self, filters: Dict[str, Any]) -> int:
        await self._ensure_table()
        where, params = self._build_where(filters)
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                f'SELECT COUNT(*) FROM "{self.table}"{where}', *params
            )

    async def exists(self, filters: Dict[str, Any]) -> bool:
        return await self.count(filters) > 0

    async def insert_one(self, data: Dict[str, Any]) -> str:
        await self._ensure_table()
        doc = dict(data)
        doc_id = str(doc.pop("_id", None) or uuid.uuid4())
        async with self.pool.acquire() as conn:
            await conn.execute(
                f'INSERT INTO "{self.table}" (id, data) VALUES ($1, $2)',
                doc_id,
                json.dumps(doc, default=str)
            )
        return doc_id

    async def insert_many(self, data: List[Dict[str, Any]]) -> List[str]:
        return [await self.insert_one(doc) for doc in data]

    async def update_one(self, id: str, data: Dict[str, Any]) -> bool:
        await self._ensure_table()
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f'UPDATE "{self.table}" SET data = data || $2::jsonb WHERE id = $1',
                id,
                json.dumps(data, default=str)
            )
        return self._affected_rows(result) > 0

    async def update_many(self, filters: Dict[str, Any], data: Dict[str, Any]) -> int:
        await self._ensure_table()
        where, params = self._build_where(filters)
        params.append(json.dumps(data, default=str))
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f'UPDATE "{self.table}" SET data = data || ${len(params)}::jsonb{where}',
                *params
            )
        return self._affected_rows(result)

    async def delete_one(self, id: str) -> bool:
        await self._ensure_table()
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f'DELETE FROM "{self.table}" WHERE id = $1', id
            )
        return self._affected_rows(result) > 0

    async def delete_many(self, filters: Dict[str, Any]) -> int:
        await self._ensure_table()
        where, params = self._build_where(filters)
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f'DELETE FROM "{self.table}"{where}', *params
            )
        return self._affected_rows(result)

    @staticmethod
    def _affected_rows(command_tag: str) -> int:
        # asyncpg returns command tags like "UPDATE 3" or "DELETE 1"
        return int(command_tag.split()[-1])
