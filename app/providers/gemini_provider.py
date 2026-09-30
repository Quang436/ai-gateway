from typing import List, Dict, Optional
from google import genai
from google.genai import types
from app.providers.base import BaseLLMProvider, LLMResponse
from app.core.config import settings

class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        # Client google-genai chính thức
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY or "dummy-key")
        self.default_model = "gemini-3.5-flash-lite"

    async def chat_complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        response_format: str = "text"
    ) -> LLMResponse:
        chosen_model = model or self.default_model
        
        # Cấu hình generation config
        generation_kwargs = {"temperature": temperature}
        if response_format == "json_object":
            generation_kwargs["response_mime_type"] = "application/json"
        
        config = types.GenerateContentConfig(**generation_kwargs)
        
        # Chuyển format messages sang dạng text prompt cho Gemini
        prompt_parts = []
        for msg in messages:
            prompt_parts.append(f"{msg.get('role', 'user')}: {msg.get('content', '')}")
        full_prompt = "\n".join(prompt_parts)

        # Gọi bất đồng bộ của Google GenAI SDK kèm cơ chế tự phục hồi model
        try:
            response = await self.client.aio.models.generate_content(
                model=chosen_model,
                contents=full_prompt,
                config=config,
            )
        except Exception as e:
            # Nếu model được yêu cầu bị 429 quota hoặc 404/503, tự động chuyển về gemini-3.5-flash-lite
            if chosen_model != "gemini-3.5-flash-lite":
                print(f"[GeminiProvider] Model '{chosen_model}' failed ({e}). Auto-switching to 'gemini-3.5-flash-lite'...")
                chosen_model = "gemini-3.5-flash-lite"
                response = await self.client.aio.models.generate_content(
                    model=chosen_model,
                    contents=full_prompt,
                    config=config,
                )
            else:
                raise e

        # Trích xuất token usage nếu có
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = response.usage_metadata.prompt_token_count or 0
            completion_tokens = response.usage_metadata.candidates_token_count or 0

        return LLMResponse(
            content=response.text or "",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model=chosen_model,
            provider="gemini"
        )

    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7
    ):
        chosen_model = model or self.default_model
        formatted_contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            formatted_contents.append({
                "role": role,
                "parts": [{"text": m["content"]}]
            })

        try:
            # Gọi Google Gemini API bằng phương thức stream
            response = await self.client.aio.models.generate_content_stream(
                model=chosen_model,
                contents=formatted_contents,
                config={"temperature": temperature}
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            if chosen_model != "gemini-3.5-flash-lite":
                print(f"[GeminiProvider Stream] Model '{chosen_model}' failed ({e}). Auto-switching to 'gemini-3.5-flash-lite'...")
                response = await self.client.aio.models.generate_content_stream(
                    model="gemini-3.5-flash-lite",
                    contents=formatted_contents,
                    config={"temperature": temperature}
                )
                async for chunk in response:
                    if chunk.text:
                        yield chunk.text
            else:
                raise e