from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.config.pyobjectid import PyObjectId

class ChatRoom(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId  # 유저의 ObjectId 참조
    admin_id: PyObjectId  # 고정 관리자 ObjectId
    last_message: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {PyObjectId: str}
        arbitrary_types_allowed = True
        allow_population_by_field_name = True

