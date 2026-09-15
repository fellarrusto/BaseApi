"""
Lifecycle of the shared HTTP client and factories of the connectors.

Add one factory per capability, the only place that knows which provider
is active, e.g.:

    def get_geocoding_client() -> BaseGeocodingClient:
        return NominatimClient(get_http_client(), base_url=settings.GEOCODING_BASE_URL)
"""
from typing import Optional

import httpx

from app.core.config import settings


class Clients:
    http: Optional[httpx.AsyncClient] = None


clients = Clients()


async def integrations_connect() -> None:
    # One shared connection pool for every connector; retries cover connection failures only
    clients.http = httpx.AsyncClient(
        timeout=settings.HTTP_TIMEOUT_SECONDS,
        transport=httpx.AsyncHTTPTransport(retries=2)
    )


async def integrations_disconnect() -> None:
    if clients.http:
        await clients.http.aclose()


def get_http_client() -> httpx.AsyncClient:
    """Shared HTTP client, for connector factories only: services never call it directly."""
    return clients.http
