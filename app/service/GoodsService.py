import os
from datetime import datetime
from typing import Optional
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException, UploadFile
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError
from app.models.Goods import Goods
from app.database import db

goods_collection = db["goods"]
user_collection = db["users"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "static", "images", "goods")

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)  # 디렉토리가 없으면 생성

class GoodsService:
    @staticmethod
    async def add_goods(goods: Goods) -> Optional[dict]:
        """상품 등록"""
        try:
            result = await goods_collection.insert_one(goods.dict(by_alias=True))
            return {"_id": str(result.inserted_id)}
        except DuplicateKeyError:
            return None  # 중복 상품 처리
        except ValidationError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

    @staticmethod
    async def delete_goods(goods_id: str) -> bool:
        """상품 삭제"""
        result = await goods_collection.delete_one({"_id": ObjectId(goods_id)})
        return result.deleted_count == 1

    @staticmethod
    async def purchase_goods(user_id: str, goods_id: str, quantity: int) -> bool:
        """상품 구매"""
        goods = await goods_collection.find_one({"_id": ObjectId(goods_id)})
        user = await user_collection.find_one({"user_id": user_id})

        if goods and user and goods["stock"] >= quantity:
            # 재고 감소
            await goods_collection.update_one(
                {"_id": ObjectId(goods_id)},
                {"$inc": {"stock": -quantity}}
            )
            # 구매 내역 추가
            purchase = {
                "goods_id": goods_id,
                "quantity": quantity,
                "purchase_date": datetime.utcnow()
            }
            await user_collection.update_one(
                {"user_id": user_id},
                {"$push": {"purchase_history": purchase}}
            )
            return True
        return False

    @staticmethod
    async def set_goods_visibility(goods_id: str, is_active: bool) -> bool:
        """상품 비공개/공개 처리"""
        if not ObjectId.is_valid(goods_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 상품 ID입니다.")

        goods = await goods_collection.find_one({"_id": ObjectId(goods_id)})
        if not goods:
            raise HTTPException(status_code=404, detail="해당 상품을 찾을 수 없습니다.")

        result = await goods_collection.update_one(
            {"_id": ObjectId(goods_id)},
            {"$set": {"is_active": is_active}}
        )
        return result.modified_count == 1


    @staticmethod
    async def update_discount(goods_id: str, discount_rate: float) -> bool:
        """상품 할인율 조정"""
        if not (0 <= discount_rate <= 1):
            raise HTTPException(status_code=400, detail="할인율은 0과 1 사이 값이어야 합니다.")

        if not ObjectId.is_valid(goods_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 상품 ID입니다.")

        goods = await goods_collection.find_one({"_id": ObjectId(goods_id)})
        if not goods:
            raise HTTPException(status_code=404, detail="해당 상품을 찾을 수 없습니다.")

        result = await goods_collection.update_one(
            {"_id": ObjectId(goods_id)},
            {"$set": {"discount_rate": discount_rate}}
        )
        return result.modified_count == 1

    @staticmethod
    async def all_goods() -> list[Goods]:
        try:
            goods_cursor = goods_collection.find({"is_active": True})
            goods_list = []

            # Cursor로 가져온 문서들을 순회하며 변환
            async for goods in goods_cursor:
                goods_obj = Goods(**goods)
                goods_list.append(goods_obj)

            return goods_list
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"상품 조회 중 오류 발생: {str(e)}")

    @staticmethod
    async def save_image(file: UploadFile) -> str:
        """이미지 파일 저장"""
        if file.content_type not in ["image/jpeg", "image/png"]:
            raise HTTPException(status_code=400, detail="JPEG 또는 PNG 형식의 파일만 업로드 가능합니다.")

        file_extension = file.filename.split(".")[-1]
        file_name = f"{uuid4()}.{file_extension}"  # 고유한 파일 이름 생성
        file_path = os.path.join(IMAGE_DIR, file_name)

        try:
            with open(file_path, "wb") as image_file:
                image_file.write(await file.read())
            return file_name
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"이미지 저장 중 오류 발생: {str(e)}")

    @staticmethod
    async def get_goods_by_id(goods_id: str) -> Optional[dict]:
        """상품 ID로 상품 정보 조회"""
        if not ObjectId.is_valid(goods_id):
            raise HTTPException(status_code=400, detail="유효하지 않은 상품 ID입니다.")
        goods = await goods_collection.find_one({"_id": ObjectId(goods_id)})
        if not goods:
            raise HTTPException(status_code=404, detail="해당 상품을 찾을 수 없습니다.")
        goods["_id"] = str(goods["_id"])
        return goods

