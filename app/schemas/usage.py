from pydantic import BaseModel, Field
from typing import List

class ProviderBreakdown(BaseModel):
    provider: str
    total_requests: int
    total_tokens: int
    estimated_cost_usd: float

class UsageSummaryResponse(BaseModel):
    # Khớp chính xác với trường mẫu của đề bài
    requests: int = Field(..., description="Tổng số requests")
    tokens: int = Field(..., description="Tổng số tokens tiêu thụ")
    average_latency_ms: float = Field(..., description="Độ trễ trung bình (ms)")
    error_rate: float = Field(..., description="Tỷ lệ yêu cầu bị lỗi (failed_requests / requests)")

    # Các trường chi tiết phục vụ Observability chuyên sâu
    client_id: str
    successful_requests: int
    failed_requests: int
    cache_hit_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_estimated_cost_usd: float
    breakdown_by_provider: List[ProviderBreakdown]