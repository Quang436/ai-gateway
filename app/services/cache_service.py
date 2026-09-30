import hashlib
import json
from typing import List, Dict, Optional, Any
from app.core.redis import redis_client

class ResponseCacheService:
    @staticmethod
    def _generate_key(model: Optional[str], messages: List[Dict[str, Any]], response_format: Optional[str] = "text") -> str:
        """
        Băm model + format + nội dung messages thành chuỗi băm SHA-256 duy nhất.
        Đảm bảo nếu cùng câu hỏi, cùng format và cùng model thì key sinh ra luôn trùng nhau.
        """
        raw_payload = f"{model or 'default'}:{response_format or 'text'}:{json.dumps(messages, sort_keys=True)}"
        hash_val = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
        return f"cache:llm:{hash_val}"

    @classmethod
    async def get_response(cls, model: Optional[str], messages: List[Dict[str, Any]], response_format: Optional[str] = "text") -> Optional[Dict[str, Any]]:
        key = cls._generate_key(model, messages, response_format)
        cached_data = await redis_client.get(key)
        if cached_data:
            return json.loads(cached_data)
        return None

    @classmethod
    async def set_response(
        cls, 
        model: Optional[str], 
        messages: List[Dict[str, Any]], 
        response_data: Dict[str, Any], 
        ttl_seconds: int = 3600,
        response_format: Optional[str] = "text"
    ) -> None:
        """
        Lưu kết quả vào Redis với hạn sống mặc định 1 giờ (3600 giây).
        """
        key = cls._generate_key(model, messages, response_format)
        await redis_client.setex(key, ttl_seconds, json.dumps(response_data))