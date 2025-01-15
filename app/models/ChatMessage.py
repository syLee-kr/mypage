from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.config.pyobjectid import PyObjectId


class ChatMessage(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    chat_room_id: str  # ChatRoom의 ObjectId 참조
    sender_id: str  # 사용자 `user_id` 문자열
    receiver_id: str  # 사용자 `user_id` 문자열
    message: Optional[str] = None
    image: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_type: str = "text"

    class Config:
        json_encoders = {
            PyObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        arbitrary_types_allowed = True
        populate_by_name = True