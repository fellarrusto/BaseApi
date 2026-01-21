# Base API - FastAPI MongoDB Boilerplate

Template modulare per API REST con FastAPI, MongoDB e supporto MCP (Model Context Protocol) per integrazione con modelli AI.

## Stack Tecnologico

| Tecnologia | Versione | Scopo |
|------------|----------|-------|
| FastAPI | ≥0.115.0 | Framework web async |
| MongoDB | 6 | Database NoSQL |
| Motor | 3.3.2 | Driver MongoDB asincrono |
| Pydantic | ≥2.5.0 | Validazione dati e settings |
| MCP | ≥1.0.0 | Model Context Protocol |
| Docker | - | Containerizzazione |

---

## Quick Start

```bash
# Clona e avvia
git clone <repo-url>
cd BaseApi
docker-compose up -d
```

**Servizi disponibili:**
- API REST: `http://localhost:5008/api/v1`
- MCP Server: `http://localhost:5009`
- Mongo Express: `http://localhost:8081` (admin/admin)
- Swagger UI: `http://localhost:5008/docs`

---

## Struttura del Progetto

```
app/
├── api/                    # Router HTTP (endpoints)
│   ├── __init__.py
│   ├── health_router.py
│   └── log_router.py
│
├── services/               # Business logic layer
│   ├── __init__.py
│   ├── health_service.py
│   └── log_service.py
│
├── models/                 # Pydantic schemas
│   ├── __init__.py
│   ├── base.py             # PyObjectId validator
│   ├── health.py
│   ├── log.py
│   └── error.py
│
├── core/                   # Configurazione e utilities
│   ├── __init__.py
│   ├── config.py           # Settings (env vars)
│   └── decorator.py        # @handle_errors, @audit_log
│
├── db/                     # Database connection
│   ├── __init__.py
│   └── database.py
│
├── mcp/                    # MCP Tools per AI
│   ├── __init__.py
│   ├── server.py           # FastMCP instance
│   ├── health_tools.py
│   └── log_tool.py
│
├── main.py                 # Entry point FastAPI
└── mcp_main.py             # Entry point MCP server
```

---

## Convenzioni di Naming

### File e Cartelle

| Tipo | Pattern | Esempio |
|------|---------|---------|
| Router | `{feature}_router.py` | `user_router.py` |
| Service | `{feature}_service.py` | `user_service.py` |
| Model | `{feature}.py` | `user.py` |
| MCP Tool | `{feature}_tools.py` | `user_tools.py` |

### Classi e Variabili

| Tipo | Pattern | Esempio |
|------|---------|---------|
| Modello DB | `{Feature}InDB` | `UserInDB` |
| Modello Response | `{Feature}Response` | `UserResponse` |
| Modello Create | `{Feature}Create` | `UserCreate` |
| Modello Update | `{Feature}Update` | `UserUpdate` |
| Classe Service | `{Feature}Service` | `UserService` |
| Istanza Service | `{feature}_service` | `user_service` |
| Router instance | `router` | `router` |
| Collection DB | `{features}` (plurale, snake_case) | `users`, `audit_logs` |

### Codice Python

- **Funzioni e variabili**: `snake_case`
- **Classi**: `PascalCase`
- **Costanti**: `UPPER_SNAKE_CASE`
- **File**: `snake_case.py`

---

## Aggiungere una Nuova Feature

Segui questi passi nell'ordine indicato per aggiungere una nuova funzionalità (esempio: `Product`).

### 1. Creare il Model

**File:** `app/models/product.py`

```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.base import PyObjectId


class ProductInDB(BaseModel):
    """Modello per persistenza su MongoDB."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    description: Optional[str] = None
    price: float
    category: str
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProductResponse(BaseModel):
    """Modello per response API."""
    id: str
    name: str
    description: Optional[str]
    price: float
    category: str
    tags: List[str]
    created_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProductCreate(BaseModel):
    """Modello per richieste POST."""
    name: str
    description: Optional[str] = None
    price: float
    category: str
    tags: List[str] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    """Modello per richieste PUT/PATCH."""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
```

**Regole per i Models:**

1. **Separazione obbligatoria**: `InDB` per database, `Response` per API, `Create`/`Update` per input
2. **ID MongoDB**: Usare sempre `PyObjectId` con `alias="_id"`
3. **Timestamp**: `created_at` con `default_factory=datetime.utcnow`
4. **Type hints**: Sempre completi, usare `Optional[]` per campi nullable
5. **Config class**: Sempre includere `json_encoders` per datetime
6. **Nessuna logica**: I models sono solo strutture dati, niente metodi di business

---

### 2. Creare il Service

**File:** `app/services/product_service.py`

```python
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from fastapi import HTTPException

from app.db.database import get_database
from app.models.product import (
    ProductInDB,
    ProductResponse,
    ProductCreate,
    ProductUpdate
)


class ProductService:
    """Service per la gestione dei prodotti."""

    def __init__(self):
        self.collection = "products"

    async def create(self, data: ProductCreate) -> ProductResponse:
        """Crea un nuovo prodotto."""
        db = get_database()

        product = ProductInDB(**data.model_dump())
        result = await db[self.collection].insert_one(
            product.model_dump(by_alias=True)
        )

        created = await db[self.collection].find_one(
            {"_id": result.inserted_id}
        )
        return self._to_response(created)

    async def get_by_id(self, product_id: str) -> ProductResponse:
        """Recupera un prodotto per ID."""
        db = get_database()

        if not ObjectId.is_valid(product_id):
            raise HTTPException(status_code=400, detail="ID non valido")

        product = await db[self.collection].find_one(
            {"_id": ObjectId(product_id)}
        )

        if not product:
            raise HTTPException(status_code=404, detail="Prodotto non trovato")

        return self._to_response(product)

    async def get_all(
        self,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[ProductResponse]:
        """Recupera tutti i prodotti con filtri opzionali."""
        db = get_database()

        query = {}
        if category:
            query["category"] = category

        cursor = db[self.collection].find(query).limit(limit)
        products = await cursor.to_list(length=limit)

        return [self._to_response(p) for p in products]

    async def update(
        self,
        product_id: str,
        data: ProductUpdate
    ) -> ProductResponse:
        """Aggiorna un prodotto esistente."""
        db = get_database()

        if not ObjectId.is_valid(product_id):
            raise HTTPException(status_code=400, detail="ID non valido")

        update_data = {
            k: v for k, v in data.model_dump().items()
            if v is not None
        }
        update_data["updated_at"] = datetime.utcnow()

        result = await db[self.collection].find_one_and_update(
            {"_id": ObjectId(product_id)},
            {"$set": update_data},
            return_document=True
        )

        if not result:
            raise HTTPException(status_code=404, detail="Prodotto non trovato")

        return self._to_response(result)

    async def delete(self, product_id: str) -> bool:
        """Elimina un prodotto."""
        db = get_database()

        if not ObjectId.is_valid(product_id):
            raise HTTPException(status_code=400, detail="ID non valido")

        result = await db[self.collection].delete_one(
            {"_id": ObjectId(product_id)}
        )

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Prodotto non trovato")

        return True

    def _to_response(self, doc: dict) -> ProductResponse:
        """Converte documento MongoDB in ProductResponse."""
        return ProductResponse(
            id=str(doc["_id"]),
            name=doc["name"],
            description=doc.get("description"),
            price=doc["price"],
            category=doc["category"],
            tags=doc.get("tags", []),
            created_at=doc["created_at"]
        )


# Istanza singleton
product_service = ProductService()
```

**Regole per i Services:**

1. **Una classe per feature**: `ProductService` gestisce solo i prodotti
2. **Singleton**: Esportare sempre un'istanza `product_service = ProductService()`
3. **Metodi async**: Tutte le operazioni DB devono essere async
4. **Ritorno tipizzato**: Ritornare sempre modelli Pydantic (`Response` o `InDB`)
5. **Validazione ID**: Controllare sempre `ObjectId.is_valid()` prima di query
6. **HTTPException**: Lanciare eccezioni FastAPI per errori (404, 400, etc.)
7. **Metodo helper privato**: `_to_response()` per conversione documento → response
8. **Collection nel costruttore**: Definire il nome collection in `__init__`

---

### 3. Creare il Router

**File:** `app/api/product_router.py`

```python
from typing import List, Optional
from fastapi import APIRouter, Query, status

from app.core.decorator import handle_errors, audit_log
from app.models.product import (
    ProductResponse,
    ProductCreate,
    ProductUpdate
)
from app.services.product_service import product_service


router = APIRouter(prefix="/products", tags=["products"])


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED
)
@handle_errors
@audit_log(method="POST", metadata={"service": "products"})
async def create_product(data: ProductCreate) -> ProductResponse:
    """Crea un nuovo prodotto."""
    return await product_service.create(data)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK
)
@handle_errors
@audit_log(method="GET", metadata={"service": "products"})
async def get_product(product_id: str) -> ProductResponse:
    """Recupera un prodotto per ID."""
    return await product_service.get_by_id(product_id)


@router.get(
    "/",
    response_model=List[ProductResponse],
    status_code=status.HTTP_200_OK
)
@handle_errors
@audit_log(method="GET", metadata={"service": "products"})
async def get_products(
    category: Optional[str] = Query(None, description="Filtra per categoria"),
    limit: int = Query(100, ge=1, le=1000, description="Limite risultati")
) -> List[ProductResponse]:
    """Recupera tutti i prodotti con filtri opzionali."""
    return await product_service.get_all(category=category, limit=limit)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK
)
@handle_errors
@audit_log(method="PUT", metadata={"service": "products"})
async def update_product(
    product_id: str,
    data: ProductUpdate
) -> ProductResponse:
    """Aggiorna un prodotto esistente."""
    return await product_service.update(product_id, data)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
@handle_errors
@audit_log(method="DELETE", metadata={"service": "products"})
async def delete_product(product_id: str) -> None:
    """Elimina un prodotto."""
    await product_service.delete(product_id)
```

**Regole per i Router:**

1. **Un router per feature**: File separato per ogni dominio
2. **Prefix e tags**: Sempre definire `prefix="/feature"` e `tags=["feature"]`
3. **Decoratori obbligatori**: Sempre applicare `@handle_errors` e `@audit_log`
4. **Ordine decoratori**: `@router.method` → `@handle_errors` → `@audit_log` → `async def`
5. **response_model**: Sempre specificare il modello di risposta
6. **status_code esplicito**: Usare `status.HTTP_*` per chiarezza
7. **Type hints**: Return type sempre specificato
8. **Docstring**: Breve descrizione per ogni endpoint (visibile in Swagger)
9. **Query params**: Usare `Query()` con description per documentazione
10. **Nessuna logica**: Il router chiama solo il service, niente business logic

---

### 4. Registrare il Router

**File:** `app/main.py`

Aggiungere l'import e includere il router:

```python
from app.api import health_router, log_router, product_router  # Aggiunto

# ...

router = APIRouter(prefix="/api/v1")
router.include_router(health_router.router)
router.include_router(log_router.router)
router.include_router(product_router.router)  # Aggiunto
```

---

### 5. (Opzionale) Creare MCP Tool

**File:** `app/mcp/product_tools.py`

```python
from typing import Optional
from bson import ObjectId

from app.mcp.server import mcp
from app.db.database import get_mcp_database
from app.models.product import ProductInDB


@mcp.tool()
async def get_product(product_id: str) -> str:
    """
    Recupera i dettagli di un prodotto.

    Args:
        product_id: ID del prodotto da cercare

    Returns:
        Dettagli del prodotto o messaggio di errore
    """
    db = await get_mcp_database()

    if not ObjectId.is_valid(product_id):
        return "Errore: ID prodotto non valido"

    product = await db["products"].find_one({"_id": ObjectId(product_id)})

    if not product:
        return "Prodotto non trovato"

    return (
        f"Prodotto: {product['name']}\n"
        f"Descrizione: {product.get('description', 'N/A')}\n"
        f"Prezzo: €{product['price']:.2f}\n"
        f"Categoria: {product['category']}"
    )


@mcp.tool()
async def search_products(
    category: Optional[str] = None,
    max_price: Optional[float] = None,
    limit: int = 10
) -> str:
    """
    Cerca prodotti con filtri opzionali.

    Args:
        category: Filtra per categoria (opzionale)
        max_price: Prezzo massimo (opzionale)
        limit: Numero massimo di risultati (default: 10)

    Returns:
        Lista dei prodotti trovati
    """
    db = await get_mcp_database()

    query = {}
    if category:
        query["category"] = category
    if max_price:
        query["price"] = {"$lte": max_price}

    cursor = db["products"].find(query).limit(limit)
    products = await cursor.to_list(length=limit)

    if not products:
        return "Nessun prodotto trovato con i criteri specificati"

    result = []
    for p in products:
        result.append(f"- {p['name']} (€{p['price']:.2f}) - {p['category']}")

    return f"Trovati {len(products)} prodotti:\n" + "\n".join(result)


@mcp.tool()
async def create_product(
    name: str,
    price: float,
    category: str,
    description: Optional[str] = None
) -> str:
    """
    Crea un nuovo prodotto.

    Args:
        name: Nome del prodotto
        price: Prezzo del prodotto
        category: Categoria del prodotto
        description: Descrizione opzionale

    Returns:
        Conferma creazione con ID del nuovo prodotto
    """
    db = await get_mcp_database()

    product = ProductInDB(
        name=name,
        price=price,
        category=category,
        description=description
    )

    result = await db["products"].insert_one(product.model_dump(by_alias=True))

    return f"Prodotto creato con successo! ID: {result.inserted_id}"
```

**Registrare il tool in** `app/mcp/__init__.py`:

```python
from app.mcp.server import mcp
from app.mcp import health_tools
from app.mcp import log_tool
from app.mcp import product_tools  # Aggiunto


def run_mcp():
    mcp.run(transport="sse")
```

**Regole per MCP Tools:**

1. **Decorator `@mcp.tool()`**: Obbligatorio per esporre la funzione
2. **Funzioni async**: Sempre usare `async def`
3. **Docstring dettagliata**: Descrivere Args e Returns (usato da Claude)
4. **Ritorno stringa**: Sempre ritornare `str` leggibile
5. **Usare `get_mcp_database()`**: Mai `get_database()` (event loop diverso)
6. **Gestione errori**: Ritornare messaggi di errore user-friendly, non eccezioni
7. **Parametri tipizzati**: Type hints completi per tutti i parametri
8. **Valori default**: Usare `Optional` con default per parametri opzionali

---

## Decoratori Disponibili

### @handle_errors

Cattura tutte le eccezioni e le converte in `HTTPException` con traceback.

```python
@router.get("/")
@handle_errors
async def my_endpoint():
    # Se qualcosa va storto, ritorna 500 con dettagli
    ...
```

### @audit_log

Registra automaticamente ogni chiamata nel database (collection `audit_logs`).

```python
@router.get("/")
@handle_errors
@audit_log(method="GET", metadata={"service": "my_service"})
async def my_endpoint():
    ...
```

**Campi registrati:**
- `action`: Nome della funzione
- `endpoint`: Path dell'endpoint
- `method`: HTTP method
- `status`: "success" o "error"
- `duration_ms`: Tempo di esecuzione
- `metadata`: Dati custom
- `timestamp`: Data/ora chiamata

---

## Configurazione

### Variabili d'Ambiente

**File:** `.env`

```env
# Porte
API_PORT=5008
MCP_PORT=5009
MONGO_EXPRESS_PORT=8081

# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGO_DB=base_api_db
MONGO_VERSION=6

# MCP
MCP_API_KEY=your-secret-key
MCP_SERVER_URL=http://localhost:5009

# Mongo Express
MONGO_EXPRESS_VERSION=1.0.0-alpha.4
MONGO_EXPRESS_USER=admin
MONGO_EXPRESS_PASSWORD=admin
```

### Aggiungere Nuove Variabili

**File:** `app/core/config.py`

```python
class Settings(BaseSettings):
    # Aggiungi qui nuove variabili
    MY_NEW_VAR: str = "default_value"
    MY_NEW_INT: int = 42

    class Config:
        env_file = ".env"
```

---

## Docker

### Comandi Utili

```bash
# Avvia tutti i servizi
docker-compose up -d

# Rebuild dopo modifiche
docker-compose up -d --build

# Logs
docker-compose logs -f base-api
docker-compose logs -f base-mcp

# Stop
docker-compose down

# Stop e rimuovi volumi
docker-compose down -v
```

### Architettura Container

```
┌─────────────────┐     ┌─────────────────┐
│    base-api     │     │    base-mcp     │
│   (FastAPI)     │     │  (MCP Server)   │
│   porta 5008    │     │   porta 5009    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────┴──────┐
              │  base-mongo │
              │  (MongoDB)  │
              │ porta 27017 │
              └──────┬──────┘
                     │
         ┌───────────┴───────────┐
         │   base-mongo-express  │
         │    (Admin UI)         │
         │     porta 8081        │
         └───────────────────────┘
```

---

## Stile del Codice

### Imports

Ordine obbligatorio:

```python
# 1. Standard library
from datetime import datetime
from typing import List, Optional
import time

# 2. Third-party
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from bson import ObjectId

# 3. Local imports
from app.core.config import settings
from app.db.database import get_database
from app.models.product import ProductResponse
```

### Type Hints

Sempre completi:

```python
# ✅ Corretto
async def get_products(limit: int = 100) -> List[ProductResponse]:
    ...

# ❌ Sbagliato
async def get_products(limit=100):
    ...
```

### Docstring

Formato Google style per funzioni pubbliche:

```python
async def create_product(data: ProductCreate) -> ProductResponse:
    """
    Crea un nuovo prodotto nel database.

    Args:
        data: Dati del prodotto da creare

    Returns:
        Il prodotto creato con ID assegnato

    Raises:
        HTTPException: Se la validazione fallisce
    """
    ...
```

### Async/Await

Tutte le operazioni I/O devono essere async:

```python
# ✅ Corretto
async def get_product(product_id: str) -> ProductResponse:
    result = await db.products.find_one({"_id": ObjectId(product_id)})
    return ProductResponse(**result)

# ❌ Sbagliato (blocca l'event loop)
def get_product(product_id: str) -> ProductResponse:
    result = db.products.find_one({"_id": ObjectId(product_id)})
    return ProductResponse(**result)
```

---

## Checklist Nuova Feature

- [ ] Model creato in `app/models/{feature}.py`
  - [ ] `{Feature}InDB` con `PyObjectId` e `alias="_id"`
  - [ ] `{Feature}Response` per output API
  - [ ] `{Feature}Create` per input POST
  - [ ] `{Feature}Update` per input PUT/PATCH (opzionale)
- [ ] Service creato in `app/services/{feature}_service.py`
  - [ ] Classe `{Feature}Service`
  - [ ] Metodi CRUD async
  - [ ] Istanza singleton esportata
- [ ] Router creato in `app/api/{feature}_router.py`
  - [ ] `prefix` e `tags` configurati
  - [ ] Decoratori `@handle_errors` e `@audit_log` applicati
  - [ ] `response_model` e `status_code` specificati
- [ ] Router registrato in `app/main.py`
- [ ] (Opzionale) MCP tool in `app/mcp/{feature}_tools.py`
  - [ ] Funzioni con `@mcp.tool()`
  - [ ] Import aggiunto in `app/mcp/__init__.py`

---

## API Endpoints Esistenti

| Method | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/v1/health/check` | Health check dell'API |
| GET | `/api/v1/logs/audit` | Recupera audit logs per range date |

**Parametri `/logs/audit`:**
- `start_date`: Data inizio (formato: DD-MM-YYYY)
- `end_date`: Data fine (formato: DD-MM-YYYY)

---

## MCP Tools Esistenti

| Tool | Descrizione |
|------|-------------|
| `health_check` | Verifica stato dell'API |
| `get_audit_logs` | Recupera log di audit per range date |

---

## Troubleshooting

### MongoDB Connection Error

```bash
# Verifica che MongoDB sia attivo
docker-compose ps base-mongo

# Controlla i log
docker-compose logs base-mongo
```

### MCP Server Non Risponde

```bash
# Verifica stato container
docker-compose ps base-mcp

# Restart
docker-compose restart base-mcp
```

### Import Error

Verifica che `PYTHONPATH` sia configurato:

```bash
# Nel container
export PYTHONPATH=/app
```

---

## License

MIT
