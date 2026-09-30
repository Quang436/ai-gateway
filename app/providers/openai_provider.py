from typing import List, Dict, Optional
from openai import AsyncOpenAI
from app.providers.base import BaseLLMProvider, LLMResponse
from app.core.config import settings

class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or "dummy-key")
        self.default_model = "gpt-4o-mini"

    async def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        response_format: Optional[object] = "text"
    ) -> LLMResponse:
        target_model = model or self.default_model
        
        create_kwargs = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format == "json_object":
            create_kwargs["response_format"] = {"type": "json_object"}
        elif isinstance(response_format, dict):
            create_kwargs["response_format"] = response_format

        response = await self.client.chat.completions.create(**create_kwargs)
        usage = response.usage
        
        return LLMResponse(
            content=response.choices[0].message.content or "",
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            model=target_model,
            provider="openai"
        )

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7
    ):
        target_model = model or self.default_model
        response = await self.client.chat.completions.create(
            model=target_model,
            messages=messages,
            temperature=temperature,
            stream=True
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content