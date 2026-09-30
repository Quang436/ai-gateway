import time
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
import json
from app.db.session import get_db
from app.db.models.entities import APIClient, AIRequestLog
from app.api.middlewares.auth_guard import verify_api_key
from app.api.middlewares.rate_limiter import check_rate_limit
from app.services.cache_service import ResponseCacheService
from app.services.conversation_service import ConversationService
from app.providers.openai_provider import OpenAIProvider
from app.providers.gemini_provider import GeminiProvider

router = APIRouter(prefix="/ai", tags=["AI Gateway"])

openai_provider = OpenAIProvider()
gemini_provider = GeminiProvider()

class MessageItem(BaseModel):
    role: str = Field(..., example="user")
    content: str = Field(..., example="Xin chào, tôi tên là Quang.")

class ChatRequest(BaseModel):
    messages: List[MessageItem]
    model: Optional[str] = Field(None, example="gemini-2.5-flash")
    provider: Optional[str] = Field("gemini", example="gemini")
    enable_fallback: Optional[bool] = Field(True, description="Tự động chuyển sang provider khác khi lỗi")
    enable_cache: Optional[bool] = Field(True, description="Bật/tắt đọc/ghi bộ nhớ đệm Redis")
    conversation_id: Optional[str] = Field(None, description="ID cuộc hội thoại để duy trì ngữ cảnh")
    conservation_id: Optional[str] = Field(None, description="Alias cho conversation_id phòng khi gõ nhầm chính tả")
    temperature: Optional[float] = 0.7
    response_format: Optional[str] = Field("text", description="'text' hoặc 'json_object'")

    @property
    def resolved_conversation_id(self) -> Optional[str]:
        return self.conversation_id or self.conservation_id

@router.post("/chat")
async def chat(
    request: ChatRequest,
    client: APIClient = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    # 1. Rate Limiting
    await check_rate_limit(client_id=str(client.id), limit_per_minute=client.rate_limit_per_min)

    start_time = time.time()
    endpoint = "/ai/chat"

    # 2. Xử lý Conversation & Lấy lịch sử hội thoại
    conv = await ConversationService.get_or_create_conversation(
        db=db,
        client_id=client.id,
        conversation_id=request.resolved_conversation_id
    )
    
    # Lấy lịch sử cũ đã lưu trong DB
    past_messages = await ConversationService.get_history(db=db, conversation_id=conv.id, limit=6)
    
    # Ghép lịch sử cũ với tin nhắn mới gửi lên
    new_messages = [m.model_dump() for m in request.messages]
    full_messages = past_messages + new_messages

    # 3. Kiểm tra Cache
    if request.enable_cache:
        cached_result = await ResponseCacheService.get_response(
            request.model, 
            full_messages, 
            response_format=request.response_format
        )
        if cached_result:
            latency_ms = int((time.time() - start_time) * 1000)
            log_entry = AIRequestLog(
                client_id=client.id,
                model=request.model or "cached",
                provider=request.provider,
                endpoint=endpoint,
                latency_ms=latency_ms,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                status="CACHE_HIT",
                error_message=None
            )
            db.add(log_entry)
            await db.commit()

            cached_result["cached"] = True
            cached_result["latency_ms"] = latency_ms
            cached_result["conversation_id"] = str(conv.id)
            return cached_result

    # 4. Gọi LLM
    status_str = "SUCCESS"
    error_msg = None
    llm_res = None
    used_provider = request.provider
    is_fallback_triggered = False

    try:
        try:
            primary_provider = openai_provider if request.provider == "openai" else gemini_provider
            llm_res = await asyncio.wait_for(
                primary_provider.chat_complete(
                    messages=full_messages,
                    model=request.model,
                    temperature=request.temperature,
                    response_format=request.response_format
                ),
                timeout=30.0
            )
        except Exception as primary_error:
            print(f"[AI-Gateway] Primary provider '{request.provider}' failed: {type(primary_error).__name__} - {primary_error}")
            if request.enable_fallback:
                is_fallback_triggered = True
                status_str = "FALLBACK"
                fallback_provider = gemini_provider if request.provider == "openai" else openai_provider
                used_provider = "gemini" if request.provider == "openai" else "openai"
                try:
                    llm_res = await asyncio.wait_for(
                        fallback_provider.chat_complete(
                            messages=full_messages,
                            model=None,
                            temperature=request.temperature,
                            response_format=request.response_format
                        ),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    status_str = "TIMEOUT"
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="AI Provider request timed out after 30 seconds."
                    )
            else:
                if isinstance(primary_error, asyncio.TimeoutError):
                    status_str = "TIMEOUT"
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="Primary AI Provider request timed out after 30 seconds."
                    )
                raise primary_error

        # 5. Lưu tin nhắn mới vào PostgreSQL
        user_prompt_text = "\n".join([m["content"] for m in new_messages if m["role"] == "user"])
        await ConversationService.save_messages(
            db=db,
            conversation_id=conv.id,
            user_content=user_prompt_text,
            assistant_content=llm_res.content,
            input_tokens=llm_res.prompt_tokens,
            output_tokens=llm_res.completion_tokens
        )

        response_payload = {
            "conversation_id": str(conv.id),
            "message": {
                "role": "assistant",
                "content": llm_res.content
            },
            "usage": {
                "prompt_tokens": llm_res.prompt_tokens,
                "completion_tokens": llm_res.completion_tokens,
                "total_tokens": llm_res.total_tokens
            },
            "provider": llm_res.provider,
            "model": llm_res.model,
            "fallback_used": is_fallback_triggered,
            "cached": False
        }

        # Lưu Cache
        if request.enable_cache:
            await ResponseCacheService.set_response(
                model=request.model,
                messages=full_messages,
                response_data=response_payload,
                ttl_seconds=3600,
                response_format=request.response_format
            )

        return response_payload

    except Exception as e:
        status_str = "FAILED"
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"All AI Providers failed: {error_msg}"
        )

    finally:
        if status_str != "CACHE_HIT":
            latency_ms = int((time.time() - start_time) * 1000)
            log_entry = AIRequestLog(
                client_id=client.id,
                model=llm_res.model if llm_res else (request.model or "unknown"),
                provider=used_provider,
                endpoint=endpoint,
                latency_ms=latency_ms,
                input_tokens=llm_res.prompt_tokens if llm_res else 0,
                output_tokens=llm_res.completion_tokens if llm_res else 0,
                total_tokens=llm_res.total_tokens if llm_res else 0,
                status=status_str,
                error_message=error_msg
            )
            db.add(log_entry)
            await db.commit()

@router.post("/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    client: APIClient = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    # 1. Rate Limiting
    await check_rate_limit(client_id=str(client.id), limit_per_minute=client.rate_limit_per_min)

    start_time = time.time()
    endpoint = "/ai/stream"

    # 2. Xử lý Conversation & Lấy lịch sử hội thoại
    conv = await ConversationService.get_or_create_conversation(
        db=db,
        client_id=client.id,
        conversation_id=request.resolved_conversation_id
    )
    past_messages = await ConversationService.get_history(db=db, conversation_id=conv.id, limit=6)
    new_messages = [m.model_dump() for m in request.messages]
    full_messages = past_messages + new_messages

    async def event_generator():
        full_response_text = ""
        used_provider = request.provider or "gemini"
        used_model = request.model or ("gpt-4o-mini" if used_provider == "openai" else "gemini-2.5-flash")
        is_fallback_triggered = False
        status_str = "SUCCESS"
        error_msg = None

        def get_provider_stream(provider_name: str, model_name: Optional[str]):
            p = openai_provider if provider_name == "openai" else gemini_provider
            return p.chat_stream(
                messages=full_messages,
                model=model_name,
                temperature=request.temperature
            )

        try:
            # 3. Kiểm tra Cache trước khi stream (tiết kiệm chi phí & thời gian)
            if request.enable_cache:
                cached_result = await ResponseCacheService.get_response(request.model, full_messages)
                if cached_result:
                    latency_ms = int((time.time() - start_time) * 1000)
                    cached_content = cached_result.get("message", {}).get("content", "")
                    tokens = cached_result.get("usage", {}).get("total_tokens", 0)

                    # Ghi nhận log CACHE_HIT
                    log_entry = AIRequestLog(
                        client_id=client.id,
                        model=request.model or "cached",
                        provider=request.provider,
                        endpoint=endpoint,
                        latency_ms=latency_ms,
                        input_tokens=0,
                        output_tokens=0,
                        total_tokens=0,
                        status="CACHE_HIT",
                        error_message=None
                    )
                    db.add(log_entry)
                    await db.commit()

                    # Trả về nội dung cache theo chuẩn SSE
                    yield f"data: {json.dumps({'content': cached_content, 'done': False})}\n\n"
                    yield f"data: {json.dumps({'done': True, 'conversation_id': str(conv.id), 'total_tokens': tokens})}\n\n"
                    yield "data: [DONE]\n\n"
                    return

            # 4. Stream từ Provider chính (kèm fallback nếu lỗi)
            try:
                stream = get_provider_stream(used_provider, request.model)
                async for chunk in stream:
                    full_response_text += chunk
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
            except Exception as primary_error:
                print(f"[AI-Gateway Stream] Primary provider '{used_provider}' failed: {primary_error}")
                if request.enable_fallback and not full_response_text:
                    is_fallback_triggered = True
                    status_str = "FALLBACK"
                    used_provider = "gemini" if used_provider == "openai" else "openai"
                    used_model = "gemini-2.5-flash" if used_provider == "gemini" else "gpt-4o-mini"
                    fallback_stream = get_provider_stream(used_provider, None)
                    async for chunk in fallback_stream:
                        full_response_text += chunk
                        yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                else:
                    raise primary_error

            # 5. Tính toán Token ước lượng
            input_text = " ".join([m.get("content", "") for m in full_messages])
            input_tokens = max(1, len(input_text.split()))
            output_tokens = max(1, len(full_response_text.split()))
            total_tokens = input_tokens + output_tokens

            # 6. Lưu tin nhắn vào PostgreSQL
            user_prompt_text = "\n".join([m["content"] for m in new_messages if m["role"] == "user"])
            await ConversationService.save_messages(
                db=db,
                conversation_id=conv.id,
                user_content=user_prompt_text,
                assistant_content=full_response_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

            # 7. Lưu Cache cho các request sau
            if request.enable_cache and full_response_text:
                await ResponseCacheService.set_response(
                    model=request.model,
                    messages=full_messages,
                    response_data={
                        "conversation_id": str(conv.id),
                        "message": {"role": "assistant", "content": full_response_text},
                        "usage": {
                            "prompt_tokens": input_tokens,
                            "completion_tokens": output_tokens,
                            "total_tokens": total_tokens
                        },
                        "provider": used_provider,
                        "model": used_model
                    },
                    ttl_seconds=3600
                )

            # 8. Báo hiệu hoàn tất stream với chunk JSON chứa done: true, conversation_id, total_tokens
            yield f"data: {json.dumps({'done': True, 'conversation_id': str(conv.id), 'total_tokens': total_tokens})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            status_str = "FAILED"
            error_msg = str(e)
            yield f"data: {json.dumps({'error': error_msg, 'done': True})}\n\n"

        finally:
            if status_str != "CACHE_HIT":
                latency_ms = int((time.time() - start_time) * 1000)
                input_text = " ".join([m.get("content", "") for m in full_messages])
                input_tokens = max(1, len(input_text.split()))
                output_tokens = max(1, len(full_response_text.split())) if full_response_text else 0
                total_tokens = input_tokens + output_tokens if full_response_text else 0

                log_entry = AIRequestLog(
                    client_id=client.id,
                    model=used_model,
                    provider=used_provider,
                    endpoint=endpoint,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    status=status_str,
                    error_message=error_msg
                )
                db.add(log_entry)
                await db.commit()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )