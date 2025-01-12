from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional, List

from app.config.pyobjectid import PyObjectId


class User(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str
    password: str
    name: str
    phone: str
    birthday: Optional[str] = None
    profile_image: Optional[str] = "profile.png"
    role: str = "user"  # 기본값 "user", 관리자일 경우 "admin"

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True