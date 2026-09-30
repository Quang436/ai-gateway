import uuid
import time
import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.entities import APIClient, AIRequestLog
from app.api.middlewares.auth_guard import verify_api_key
from app.api.middlewares.rate_limiter import check_rate_limit
from app.core.redis import redis_client
from app.providers.gemini_provider import GeminiProvider
from app.providers.openai_provider import OpenAIProvider

router = APIRouter(prefix="/ai", tags=["AI Gateway"])

gemini_provider = GeminiProvider()
openai_provider = OpenAIProvider()

class AnalyzeRequest(BaseModel):
    content: str = Field(..., example="Hệ thống AI Gateway giúp tiết kiệm chi phí và tăng độ tin cậy khi gọi LLM.")
    task_type: Optional[str] = Field("sentiment_and_summary", example="sentiment_and_summary", description="Loại tác vụ: 'summary', 'sentiment', 'key_entities', 'sentiment_and_summary'")
    mode: Optional[str] = Field("sync", example="sync", description="'sync' (trả kết quả ngay) hoặc 'async' (đưa vào hàng đợi nền Queue)")
    provider: Optional[str] = Field("gemini", example="gemini")
    model: Optional[str] = Field(None, example="gemini-2.5-flash")

class AnalyzeSyncResponse(BaseModel):
    task_id: str
    task_type: str
    analysis: Dict[str, Any]
    provider: str
    model: str
    latency_ms: int

class AnalyzeAsyncResponse(BaseModel):
    task_id: str
    status: str
    message: str
    check_status_url: str

async def process_analysis_in_background(
    task_id: str,
    client_id: uuid.UUID,
    content: str,
    task_type: str,
    provider_name: str,
    model_name: Optional[str]
):
    """Xử lý tác vụ phân tích nặng trong hàng đợi nền (Queue-based background task)"""
    start_time = time.time()
    redis_key = f"task:analyze:{task_id}"
    
    # Đánh dấu đang xử lý
    await redis_client.setex(redis_key, 3600, json.dumps({"status": "PROCESSING", "task_id": task_id}))

    prompt = (
        f"Hãy phân tích đoạn văn bản sau theo mục tiêu '{task_type}'.\n"
        f"Định dạng trả về BẮT BUỘC là một JSON object với các trường phù hợp (ví dụ: summary, sentiment, key_points, score).\n\n"
        f"Nội dung:\n{content}"
    )

    try:
        provider = openai_provider if provider_name == "openai" else gemini_provider
        res = await asyncio.wait_for(
            provider.chat_complete(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                response_format="json_object"
            ),
            timeout=60.0
        )
        latency_ms = int((time.time() - start_time) * 1000)

        # Parse kết quả JSON
        try:
            analysis_data = json.loads(res.content)
        except Exception:
            analysis_data = {"raw_result": res.content}

        result_payload = {
            "status": "COMPLETED",
            "task_id": task_id,
            "task_type": task_type,
            "analysis": analysis_data,
            "provider": res.provider,
            "model": res.model,
            "latency_ms": latency_ms,
            "tokens": res.total_tokens
        }
        await redis_client.setex(redis_key, 3600, json.dumps(result_payload))

    except Exception as e:
        await redis_client.setex(
            redis_key, 
            3600, 
            json.dumps({"status": "FAILED", "task_id": task_id, "error": str(e)})
        )

@router.post("/analyze", response_model=Any)
async def analyze_content(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    client: APIClient = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint phân tích văn bản/dữ liệu bằng AI với Structured Output JSON.
    Hỗ trợ chế độ đồng bộ ('sync') hoặc Hàng đợi bất đồng bộ ('async' Queue Processing).
    """
    # 1. Rate Limiting
    await check_rate_limit(client_id=str(client.id), limit_per_minute=client.rate_limit_per_min)

    task_id = str(uuid.uuid4())

    # Chế độ ASYNC: Đưa vào hàng đợi nền (Queue-based Processing)
    if request.mode == "async":
        redis_key = f"task:analyze:{task_id}"
        await redis_client.setex(redis_key, 3600, json.dumps({"status": "QUEUED", "task_id": task_id}))
        
        background_tasks.add_task(
            process_analysis_in_background,
            task_id=task_id,
            client_id=client.id,
            content=request.content,
            task_type=request.task_type,
            provider_name=request.provider,
            model_name=request.model
        )

        return AnalyzeAsyncResponse(
            task_id=task_id,
            status="QUEUED",
            message="Yêu cầu phân tích đã được đưa vào hàng đợi xử lý nền.",
            check_status_url=f"/ai/analyze/tasks/{task_id}"
        )

    # Chế độ SYNC: Xử lý và trả về kết quả ngay lập tức
    start_time = time.time()
    prompt = (
        f"Hãy phân tích đoạn văn bản sau theo mục tiêu '{request.task_type}'.\n"
        f"Định dạng trả về BẮT BUỘC là một JSON object với các trường phù hợp (ví dụ: summary, sentiment, key_points).\n\n"
        f"Nội dung:\n{request.content}"
    )

    provider = openai_provider if request.provider == "openai" else gemini_provider
    try:
        res = await asyncio.wait_for(
            provider.chat_complete(
                messages=[{"role": "user", "content": prompt}],
                model=request.model,
                response_format="json_object"
            ),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        latency_ms = int((time.time() - start_time) * 1000)
        log_entry = AIRequestLog(
            client_id=client.id,
            model=request.model or "unknown",
            provider=request.provider,
            endpoint="/ai/analyze",
            latency_ms=latency_ms,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            status="TIMEOUT",
            error_message="Phân tích yêu cầu vượt quá thời gian chờ (30s Timeout)"
        )
        db.add(log_entry)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI Provider request timed out after 30 seconds."
        )
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        log_entry = AIRequestLog(
            client_id=client.id,
            model=request.model or "unknown",
            provider=request.provider,
            endpoint="/ai/analyze",
            latency_ms=latency_ms,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            status="FAILED",
            error_message=str(e)
        )
        db.add(log_entry)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Phân tích thất bại từ AI Provider: {str(e)}"
        )

    latency_ms = int((time.time() - start_time) * 1000)

    try:
        analysis_data = json.loads(res.content)
    except Exception:
        analysis_data = {"raw_result": res.content}

    # Ghi log Audit vào PostgreSQL
    log_entry = AIRequestLog(
        client_id=client.id,
        model=res.model,
        provider=res.provider,
        endpoint="/ai/analyze",
        latency_ms=latency_ms,
        input_tokens=res.prompt_tokens,
        output_tokens=res.completion_tokens,
        total_tokens=res.total_tokens,
        status="SUCCESS",
        error_message=None
    )
    db.add(log_entry)
    await db.commit()

    return AnalyzeSyncResponse(
        task_id=task_id,
        task_type=request.task_type,
        analysis=analysis_data,
        provider=res.provider,
        model=res.model,
        latency_ms=latency_ms
    )

@router.get("/analyze/tasks/{task_id}")
async def get_analysis_task_status(
    task_id: str,
    client: APIClient = Depends(verify_api_key)
):
    """Kiểm tra trạng thái & nhận kết quả của tác vụ phân tích chạy ngầm trong Hàng đợi"""
    redis_key = f"task:analyze:{task_id}"
    raw = await redis_client.get(redis_key)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task ID '{task_id}' không tồn tại hoặc đã hết hạn (TTL 1h)."
        )
    return json.loads(raw)
