from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional

from app.config.pyobjectid import PyObjectId
from datetime import datetime

class Goods(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    name: str
    description: str
    # 상품 설명 (필수).
    price: float
    stock: int
    image_url: Optional[str]
    category: Optional[str]
    discount_rate: Optional[float] = 0.0
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    # 상품 활성화 여부 (기본값: True).
    sku: Optional[str]
    # 상품 고유 식별 번호 (선택, 재고 관리 등에서 사용 가능).
    shipping_cost: Optional[float] = 0.0
    # 상품의 배송비 (선택, 기본값: 0.0).

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True

