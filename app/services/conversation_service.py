import uuid
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.entities import Conversation, Message

class ConversationService:
    @staticmethod
    async def get_or_create_conversation(
        db: AsyncSession, 
        client_id: uuid.UUID, 
        conversation_id: str | None = None,
        title: str | None = None
    ) -> Conversation:
        if conversation_id:
            try:
                cleaned_id = str(conversation_id).strip().strip("'").strip('"')
                conv_uuid = uuid.UUID(cleaned_id)
                stmt = select(Conversation).where(
                    Conversation.id == conv_uuid,
                    Conversation.client_id == client_id
                )
                result = await db.execute(stmt)
                conv = result.scalars().first()
                if conv:
                    return conv
            except ValueError:
                pass

        # Tạo mới nếu không truyền conversation_id hoặc không tìm thấy
        new_conv = Conversation(
            client_id=client_id,
            title=title or "New Conversation"
        )
        db.add(new_conv)
        await db.commit()
        await db.refresh(new_conv)
        return new_conv

    @staticmethod
    async def get_history(
        db: AsyncSession, 
        conversation_id: uuid.UUID, 
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """Lấy tối đa N tin nhắn gần nhất để làm ngữ cảnh gửi cho AI"""
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        messages = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in messages]

    @staticmethod
    async def save_messages(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_content: str,
        assistant_content: str,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> None:
        """Lưu cả tin nhắn người dùng và câu trả lời của AI vào DB"""
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=user_content,
            tokens=input_tokens
        )
        ai_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            tokens=output_tokens
        )
        db.add_all([user_msg, ai_msg])
        await db.commit()