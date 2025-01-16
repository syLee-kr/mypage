from typing import Optional, List

from bson import ObjectId
from fastapi import HTTPException
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError

from app.config.password import hash_password, verify_password
from app.models.User import User
from app.database import db

# 유저 컬렉션 참조
user_collection = db["users"]

class UserService:
    @staticmethod
    async def is_user_id_duplicate(user_id: str) -> bool:
        """user_id 중복 확인"""
        user = await user_collection.find_one({"user_id": user_id})
        return user is not None

    @staticmethod
    async def create_user(user: User) -> Optional[dict]:
        """새로운 사용자 생성"""
        try:
            user.password = hash_password(user.password)  # 비밀번호 암호화
            result = await user_collection.insert_one(user.dict(by_alias=True))
            return {"_id": str(result.inserted_id)}
        except DuplicateKeyError:
            return None  # 중복된 user_id인 경우 None 반환
        except ValidationError as ve:
            raise HTTPException(status_code=400, detail=str(ve))

    @staticmethod
    async def check_user_role(user_id: str) -> Optional[str]:
        """유저 role 확인 (user/admin)"""
        user = await user_collection.find_one({"user_id": user_id})
        if user:
            return user.get("role", "user")  # 기본값 user 반환
        return None

    @staticmethod
    async def update_password(user_id: str, current_password: str, new_password: str) -> bool:
        """비밀번호 변경"""
        user = await user_collection.find_one({"user_id": user_id})
        if user and verify_password(current_password, user["password"]):
            new_hashed_password = hash_password(new_password)
            result = await user_collection.update_one(
                {"user_id": user_id},
                {"$set": {"password": new_hashed_password}}
            )
            return result.modified_count == 1
        return False

    @staticmethod
    async def update_profile_image(user_id: str, profile_image_url: str) -> bool:
        """프로필 이미지 업데이트"""
        result = await user_collection.update_one(
            {"user_id": user_id},
            {"$set": {"profile_image": profile_image_url}}
        )
        return result.modified_count == 1

    @staticmethod
    async def verify_user_credentials(user_id: str, password: str) -> bool:
        """사용자 자격 증명 검증"""
        user = await UserService.find_user_by_user_id(user_id)
        if not user:
            return False
        return verify_password(password, user.password)

    @staticmethod
    async def find_user_by_user_id(user_id: str) -> Optional[User]:
        """사용자 ID로 사용자 찾기"""
        user = await user_collection.find_one({"user_id": user_id})
        if user:
            try:
                user_obj = User(**user)
                return user_obj
            except ValidationError:
                raise HTTPException(status_code=500, detail="사용자 데이터가 유효하지 않습니다.")
        return None

    @staticmethod
    async def authenticate(user_id: str, password: str) -> Optional[User]:
        user = await UserService.find_user_by_user_id(user_id)
        if user and verify_password(password, user.password):
            return user
        return None

    @staticmethod
    async def list_users(page: int = 1, size: int = 20) -> List[User]:
        """모든 유저를 페이징하여 반환"""
        skip = (page - 1) * size
        users_cursor = user_collection.find().skip(skip).limit(size)
        users = [User(**user) for user in await users_cursor.to_list(length=size)]
        return users