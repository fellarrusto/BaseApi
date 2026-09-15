from typing import Any, Dict, List, Optional

from app.integrations.llm.base_llm_client import BaseLLMClient


class FakeLLMClient(BaseLLMClient):
    """LLM client for tests: returns a fixed answer and records every call."""

    def __init__(self, content: str = "fake answer") -> None:
        self.content = content
        self.calls: List[Dict[str, Any]] = []

    async def invoke(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        self.calls.append({"messages": messages, "model": model, "temperature": temperature, "max_tokens": max_tokens})
        return {"content": self.content, "model": model or "fake-model", "usage": {}}
