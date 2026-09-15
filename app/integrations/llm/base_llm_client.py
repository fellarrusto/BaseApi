from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLMClient(ABC):
    """
    Provider-agnostic chat completion contract.

    Messages use the OpenAI format: [{"role": "user", "content": "..."}].
    Returns a plain dict: {"content": str, "model": str, "usage": dict}.
    Raises ExternalServiceError on any provider failure.
    """

    @abstractmethod
    async def invoke(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        pass
