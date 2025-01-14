from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.config.pyobjectid import PyObjectId


class ChatMessage(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    chat_room_id: PyObjectId  # ChatRoom의 ObjectId 참조
    sender_id: PyObjectId  # 유저의 ObjectId 참조
    receiver_id: PyObjectId  # 유저의 ObjectId 참조
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
        allow_population_by_field_name = True