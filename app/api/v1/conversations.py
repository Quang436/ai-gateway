import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.session import get_db
from app.db.models.entities import APIClient, Conversation, Message
from app.api.middlewares.auth_guard import verify_api_key

router = APIRouter(prefix="/conversations", tags=["Conversations Management"])

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    tokens: int
    created_at: datetime

class ConversationSummary(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: datetime

class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: datetime
    messages: List[MessageOut]

@router.get("", response_model=List[ConversationSummary])
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    client: APIClient = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy danh sách tất cả các cuộc hội thoại thuộc về Client hiện tại kèm số lượng tin nhắn.
    """
    stmt = (
        select(
            Conversation.id,
            Conversation.title,
            Conversation.created_at,
            func.count(Message.id).label("message_count")
        )
        .outerjoin(Message, Conversation.id == Message.conversation_id)
        .where(Conversation.client_id == client.id)
        .group_by(Conversation.id)
        .order_by(desc(Conversation.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        ConversationSummary(
            id=str(r.id),
            title=r.title or "New Conversation",
            message_count=r.message_count,
            created_at=r.created_at
        )
        for r in rows
    ]

@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_detail(
    conversation_id: str,
    client: APIClient = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Xem toàn bộ lịch sử tin nhắn của một cuộc hội thoại cụ thể.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id.strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng conversation_id không hợp lệ (yêu cầu UUID)."
        )

    # Kiểm tra quyền sở hữu cuộc trò chuyện
    conv_stmt = select(Conversation).where(
        Conversation.id == conv_uuid,
        Conversation.client_id == client.id
    )
    conv = (await db.execute(conv_stmt)).scalars().first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuộc hội thoại không tồn tại hoặc không thuộc quyền sở hữu của bạn."
        )

    # Lấy toàn bộ tin nhắn
    msg_stmt = (
        select(Message)
        .where(Message.conversation_id == conv_uuid)
        .order_by(Message.created_at.asc())
    )
    messages = (await db.execute(msg_stmt)).scalars().all()

    return ConversationDetail(
        id=str(conv.id),
        title=conv.title or "New Conversation",
        created_at=conv.created_at,
        messages=[
            MessageOut(
                id=str(m.id),
                role=m.role,
                content=m.content,
                tokens=m.tokens or 0,
                created_at=m.created_at
            )
            for m in messages
        ]
    )

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    client: APIClient = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Xóa một cuộc hội thoại và toàn bộ tin nhắn liên quan.
    """
    try:
        conv_uuid = uuid.UUID(conversation_id.strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Định dạng conversation_id không hợp lệ."
        )

    conv_stmt = select(Conversation).where(
        Conversation.id == conv_uuid,
        Conversation.client_id == client.id
    )
    conv = (await db.execute(conv_stmt)).scalars().first()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuộc hội thoại không tồn tại."
        )

    await db.delete(conv)
    await db.commit()
    return None
