from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

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
    purchase_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    class Config:
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True  # 올바른 설정으로 수정

