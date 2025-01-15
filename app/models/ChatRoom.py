from typing import Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime

from app.config.pyobjectid import PyObjectId

class ChatRoom(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str  # 사용자 `user_id` 문자열
    admin_id: Literal["ARIES"] = Field(default="ARIES")  # 항상 "ARIES"로 고정
    last_message: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {PyObjectId: str}
        arbitrary_types_allowed = True
        populate_by_name = True

    @validator('admin_id')
    def validate_admin_id(cls, v):
        if v != "ARIES":
            raise ValueError('admin_id must be "ARIES"')
        return v