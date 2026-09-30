from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.session import engine, Base
import app.db.models.entities
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.analyze import router as analyze_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.usage import router as usage_router

from app.core.redis import redis_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo bảng cơ sở dữ liệu nếu chưa có
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Dọn dẹp kết nối khi tắt server
    await engine.dispose()
    await redis_client.aclose()
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Centralized AI Gateway with Reliability, Routing, and Usage Analytics",
    lifespan=lifespan
)

# Đăng ký toàn bộ router API Gateway
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(analyze_router)
app.include_router(conversations_router)
app.include_router(usage_router)

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)