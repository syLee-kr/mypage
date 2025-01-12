from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.config.pyobjectid import PyObjectId


class ChatMessage(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    sender_id: str
    receiver_id: str
    message: Optional[str] = None
    image: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    message_type: str

    class Config:
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True
