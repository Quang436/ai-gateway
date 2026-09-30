from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.db.session import get_db
from app.db.models.entities import APIClient, AIRequestLog
from app.api.middlewares.auth_guard import verify_api_key
from app.schemas.usage import UsageSummaryResponse, ProviderBreakdown

router = APIRouter(prefix="/usage", tags=["Analytics & Usage"])

# Bảng giá ước tính cho 1,000,000 tokens (USD)
PRICING_PER_MILLION = {
    "openai": {"input": 0.15, "output": 0.60},     # gpt-4o-mini
    "gemini": {"input": 0.075, "output": 0.30},    # gemini-2.5-flash
}

@router.get("", response_model=UsageSummaryResponse)
async def get_usage_summary(
    client: APIClient = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Thống kê toàn bộ lịch sử sử dụng token, số request, độ trễ và chi phí ước tính của Client hiện tại.
    """
    # 1. Query tổng quát các chỉ số của Client
    summary_stmt = select(
        func.count(AIRequestLog.id).label("total_requests"),
        func.sum(case((AIRequestLog.status == "SUCCESS", 1), else_=0)).label("successful_requests"),
        func.sum(case((AIRequestLog.status == "FAILED", 1), else_=0)).label("failed_requests"),
        func.sum(case((AIRequestLog.status == "CACHE_HIT", 1), else_=0)).label("cache_hit_requests"),
        func.coalesce(func.sum(AIRequestLog.input_tokens), 0).label("total_input_tokens"),
        func.coalesce(func.sum(AIRequestLog.output_tokens), 0).label("total_output_tokens"),
        func.coalesce(func.sum(AIRequestLog.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.avg(AIRequestLog.latency_ms), 0.0).label("avg_latency")
    ).where(AIRequestLog.client_id == client.id)

    summary_result = (await db.execute(summary_stmt)).first()

    # 2. Query phân tích theo từng Provider (OpenAI, Gemini)
    breakdown_stmt = select(
        AIRequestLog.provider,
        func.count(AIRequestLog.id).label("provider_requests"),
        func.coalesce(func.sum(AIRequestLog.input_tokens), 0).label("input_tokens"),
        func.coalesce(func.sum(AIRequestLog.output_tokens), 0).label("output_tokens"),
        func.coalesce(func.sum(AIRequestLog.total_tokens), 0).label("total_tokens")
    ).where(
        AIRequestLog.client_id == client.id,
        AIRequestLog.status != "FAILED"
    ).group_by(AIRequestLog.provider)

    breakdown_result = (await db.execute(breakdown_stmt)).all()

    total_cost = 0.0
    provider_breakdown_list = []

    for row in breakdown_result:
        provider_name = (row.provider or "unknown").lower()
        pricing = PRICING_PER_MILLION.get(provider_name, {"input": 0.1, "output": 0.2})
        
        cost_in = (row.input_tokens / 1_000_000) * pricing["input"]
        cost_out = (row.output_tokens / 1_000_000) * pricing["output"]
        provider_cost = cost_in + cost_out
        total_cost += provider_cost

        provider_breakdown_list.append(
            ProviderBreakdown(
                provider=row.provider or "unknown",
                total_requests=row.provider_requests,
                total_tokens=row.total_tokens,
                estimated_cost_usd=round(provider_cost, 6)
            )
        )

    total_req = summary_result.total_requests or 0
    failed_req = summary_result.failed_requests or 0
    calculated_error_rate = round(float(failed_req) / float(total_req), 4) if total_req > 0 else 0.0
    total_token_count = summary_result.total_tokens or 0

    return UsageSummaryResponse(
        requests=total_req,
        tokens=total_token_count,
        average_latency_ms=round(float(summary_result.avg_latency), 2),
        error_rate=calculated_error_rate,
        client_id=str(client.id),
        successful_requests=summary_result.successful_requests or 0,
        failed_requests=failed_req,
        cache_hit_requests=summary_result.cache_hit_requests or 0,
        total_input_tokens=summary_result.total_input_tokens or 0,
        total_output_tokens=summary_result.total_output_tokens or 0,
        total_estimated_cost_usd=round(total_cost, 6),
        breakdown_by_provider=provider_breakdown_list
    )