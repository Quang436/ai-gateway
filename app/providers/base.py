from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class LLMResponse(BaseModel):
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    provider: str

class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[str] = "text"
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7
    ):
        pass