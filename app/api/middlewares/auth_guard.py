import hashlib
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.db.session import get_db
from app.db.models.entities import APIClient

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

async def verify_api_key(
    api_key: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> APIClient:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header"
        )

    # 1. Hỗ trợ Master Key mặc định để test dev
    if api_key == settings.DEFAULT_GATEWAY_API_KEY:
        # Tìm hoặc tạo client mặc định trong DB
        hashed = hash_key(api_key)
        stmt = select(APIClient).where(APIClient.api_key_hash == hashed)
        result = await db.execute(stmt)
        client = result.scalars().first()
        
        if not client:
            client = APIClient(
                name="Default Dev Client",
                api_key_hash=hashed,
                rate_limit_per_min=100
            )
            db.add(client)
            await db.commit()
            await db.refresh(client)
        return client

    # 2. Kiểm tra key thường trong Database
    hashed = hash_key(api_key)
    stmt = select(APIClient).where(APIClient.api_key_hash == hashed)
    result = await db.execute(stmt)
    client = result.scalars().first()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return client