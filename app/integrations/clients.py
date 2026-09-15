from typing import Optional

import httpx

from app.core.config import settings
from app.integrations.llm.base_llm_client import BaseLLMClient
from app.integrations.llm.openrouter_client import OpenRouterClient


class Clients:
    http: Optional[httpx.AsyncClient] = None


clients = Clients()


async def integrations_connect() -> None:
    # One shared connection pool; retries cover connection failures only
    clients.http = httpx.AsyncClient(
        timeout=settings.HTTP_TIMEOUT_SECONDS,
        transport=httpx.AsyncHTTPTransport(retries=2)
    )


async def integrations_disconnect() -> None:
    if clients.http:
        await clients.http.aclose()


def get_llm_client() -> BaseLLMClient:
    """LLM client factory: the only place that knows which provider is active."""
    return OpenRouterClient(
        clients.http,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        default_model=settings.OPENROUTER_MODEL
    )
