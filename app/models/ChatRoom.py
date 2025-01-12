from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional

from app.config.pyobjectid import PyObjectId
from datetime import datetime

from app.models.ChatMessage import ChatMessage


class ChatRoom(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    admin_id: Optional[PyObjectId] = None
    last_message: Optional[ChatMessage] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True
