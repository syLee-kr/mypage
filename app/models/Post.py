from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.config.pyobjectid import PyObjectId
from app.models.Comment import Comment


class Post(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    author_id: str  # 게시글 작성자 ID
    content: str  # 게시글 내용
    timestamp: datetime = Field(default_factory=datetime.utcnow)  # 작성 시간
    is_public: bool = False  # 공개 여부
    likes: List[str] = []  # 좋아요를 누른 사용자 ID 목록
    image_urls: List[str] = []  # 첨부된 이미지 URL 목록
    comments: List[Comment] = []  # 댓글 목록

    class Config:
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True
        populate_by_name = True
