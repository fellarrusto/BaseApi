import logging
import time

from fastapi.routing import APIRoute
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.services.audit_log_service import audit_log_service

logger = logging.getLogger(__name__)


class AuditMiddleware:
    """
    Records every call to an API route in the audit log.

    The entry is written once the endpoint has produced its response; a
    failure while writing it is logged and never changes the response.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        status_code = 500  # kept if the app raises before responding

        async def send_with_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_status)
        finally:
            # FastAPI sets scope["route"] on match; docs and 404s are skipped
            route = scope.get("route")
            if isinstance(route, APIRoute):
                duration_ms = (time.perf_counter() - started) * 1000
                await self._record(route.name, scope["path"], scope["method"], status_code, duration_ms)

    @staticmethod
    async def _record(action: str, path: str, method: str, status_code: int, duration_ms: float) -> None:
        try:
            await audit_log_service.record(
                action=action,
                endpoint=path,
                method=method,
                status_code=status_code,
                duration_ms=duration_ms
            )
        except Exception:
            logger.exception("Failed to write audit log for %s %s", method, path)
