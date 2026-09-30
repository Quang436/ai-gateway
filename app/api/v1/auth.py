import secrets
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models.entities import APIClient
from app.api.middlewares.auth_guard import hash_key

router = APIRouter(prefix="/auth", tags=["Authentication & Key Management"])

class ClientRegisterRequest(BaseModel):
    name: str = Field(..., example="Mobile App Service", description="Tên ứng dụng / service sử dụng Gateway")
    rate_limit_per_min: int = Field(60, example=60, description="Giới hạn số request trên phút")

class ClientRegisterResponse(BaseModel):
    client_id: str
    name: str
    api_key: str = Field(..., description="API Key dùng trong header X-API-Key. CHỈ HIỂN THỊ 1 LẦN DUY NHẤT.")
    rate_limit_per_min: int
    message: str

@router.post("", response_model=ClientRegisterResponse, status_code=status.HTTP_201_CREATED)
@router.post("/register", response_model=ClientRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_client(
    request: ClientRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Cấp phát API Key mới cho một ứng dụng / service trong doanh nghiệp.
    Mã khóa thô (Raw API Key) chỉ được trả về một lần duy nhất lúc tạo.
    Database chỉ lưu trữ chuỗi băm SHA-256 an toàn.
    """
    # 1. Sinh chuỗi API Key an toàn ngẫu nhiên
    raw_api_key = f"gw-{secrets.token_urlsafe(32)}"
    hashed_key = hash_key(raw_api_key)

    # 2. Kiểm tra xem hash đã tồn tại chưa (xác suất gần như 0 nhưng vẫn check)
    stmt = select(APIClient).where(APIClient.api_key_hash == hashed_key)
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        raise HTTPException(status_code=500, detail="Key collision detected, please retry.")

    # 3. Lưu vào PostgreSQL
    new_client = APIClient(
        name=request.name,
        api_key_hash=hashed_key,
        rate_limit_per_min=request.rate_limit_per_min
    )
    db.add(new_client)
    await db.commit()
    await db.refresh(new_client)

    return ClientRegisterResponse(
        client_id=str(new_client.id),
        name=new_client.name,
        api_key=raw_api_key,
        rate_limit_per_min=new_client.rate_limit_per_min,
        message="Lưu trữ API Key cẩn thận. Khóa này chỉ hiển thị một lần duy nhất."
    )
