from fastapi import HTTPException, status
from app.core.redis import redis_client

async def check_rate_limit(client_id: str, limit_per_minute: int = 60) -> int:
    """
    Sử dụng thuật toán Fixed Window Counter trên Redis.
    Tự động reset sau 60 giây.
    """
    key = f"rate_limit:{client_id}"
    
    # Tăng biến đếm nguyên tử trong Redis
    current_count = await redis_client.incr(key)
    
    # Nếu là request đầu tiên trong chu kỳ, đặt TTL là 60s
    if current_count == 1:
        await redis_client.expire(key, 60)
        
    # Vượt ngưỡng -> Chặn ngay lập tức
    if current_count > limit_per_minute:
        ttl = await redis_client.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Rate limit exceeded. Too many requests.",
                "retry_after_seconds": ttl,
                "limit_per_minute": limit_per_minute
            }
        )
    return current_count