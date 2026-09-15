from typing import Any, Dict, List, Optional

import httpx

from app.core.exceptions import ExternalServiceError
from app.integrations.llm.base_llm_client import BaseLLMClient


class OpenRouterClient(BaseLLMClient):
    """OpenRouter chat completions (OpenAI-compatible API)."""

    def __init__(self, http: httpx.AsyncClient, api_key: str, base_url: str, default_model: str):
        self.http = http
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ExternalServiceError("OpenRouter is not configured: set OPENROUTER_API_KEY")

        payload: Dict[str, Any] = {"model": model or self.default_model, "messages": messages}
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        try:
            response = await self.http.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ExternalServiceError(f"OpenRouter returned HTTP {e.response.status_code}") from e
        except httpx.HTTPError as e:
            raise ExternalServiceError(f"OpenRouter request failed: {type(e).__name__}") from e

        body = response.json()
        return {
            "content": body["choices"][0]["message"]["content"],
            "model": body.get("model", payload["model"]),
            "usage": body.get("usage", {})
        }
