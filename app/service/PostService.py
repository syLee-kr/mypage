# app/service/PostService.py (발췌)

from typing import List, Optional
from bson import ObjectId
from pydantic import json
from pymongo import DESCENDING

from app.database import post_collection, comment_collection  # <- 이제 comment_collection 사용
from app.models.Post import Post
from app.models.Comment import Comment
from fastapi import HTTPException

class PostService:
    @staticmethod
    async def get_posts(skip: int = 0, limit: int = 10) -> List[Post]:
        pipeline = [
            {"$match": {"is_public": True}},
            {"$sort": {"timestamp": -1}},
            {"$skip": skip},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "comments",
                    "localField": "_id",
                    "foreignField": "post_id",
                    "as": "comments"
                }
            },
            {"$addFields": {"comments": {"$slice": ["$comments", 2]}}},  # 댓글 2개만 가져오기
        ]
        cursor = post_collection.aggregate(pipeline)
        posts = []
        async for doc in cursor:
            # image_urls 필드 검증 및 수정
            if "image_urls" not in doc or not isinstance(doc["image_urls"], list):
                if "image_urls" in doc and isinstance(doc["image_urls"], str):
                    try:
                        parsed_urls = json.loads(doc["image_urls"])
                        if isinstance(parsed_urls, list):
                            doc["image_urls"] = parsed_urls
                        else:
                            doc["image_urls"] = []
                    except json.JSONDecodeError:
                        doc["image_urls"] = []
                else:
                    doc["image_urls"] = []

            print(f"Post ID: {doc['_id']}, Image URLs: {doc['image_urls']}")  # 디버깅 로그
            try:
                posts.append(Post(**doc))  # Pydantic 모델로 변환
            except Exception as e:
                print(f"Error parsing post: {e}")
        return posts

    @staticmethod
    async def get_post_details(post_id: str) -> Optional[Post]:
        """
        단일 게시글 + 모든 댓글(무제한)
        """
        post_doc = await post_collection.find_one({"_id": ObjectId(post_id), "is_public": True})
        if not post_doc:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

        # 전체 댓글 불러오기
        c_cursor = comment_collection.find({"post_id": ObjectId(post_id)}) \
            .sort("timestamp", DESCENDING)
        comment_list = []
        async for c in c_cursor:
            comment_list.append(Comment(**c))

        post_doc["comments"] = comment_list
        return Post(**post_doc)
    @staticmethod
    async def create_post(post_data: dict, user_role: str) -> Optional[dict]:
        if user_role != "admin":
            raise HTTPException(status_code=403, detail="권한이 없습니다.")

        result = await post_collection.insert_one(post_data)
        if result.inserted_id:
            return {"_id": str(result.inserted_id)}
        return None

    @staticmethod
    async def update_post(post_id: str, updated_fields: dict) -> Optional[Post]:
        result = await post_collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": updated_fields}
        )
        if result.modified_count == 1:
            updated_post = await post_collection.find_one({"_id": ObjectId(post_id)})
            return Post(**updated_post)
        return None

    @staticmethod
    async def delete_post(post_id: str, user_role: str, user_id: str) -> bool:
        post = await post_collection.find_one({"_id": ObjectId(post_id)})
        if not post:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

        if user_role != "admin" and post["author_id"] != user_id:
            raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")

        result = await post_collection.delete_one({"_id": ObjectId(post_id)})
        return result.deleted_count == 1

    @staticmethod
    async def like_post(post_id: str, user_id: str) -> bool:
        post = await post_collection.find_one({"_id": ObjectId(post_id)})
        if not post:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

        if user_id in post.get("likes", []):
            # 좋아요 취소
            result = await post_collection.update_one(
                {"_id": ObjectId(post_id)},
                {"$pull": {"likes": user_id}}
            )
        else:
            # 좋아요 추가
            result = await post_collection.update_one(
                {"_id": ObjectId(post_id)},
                {"$addToSet": {"likes": user_id}}
            )
        return result.modified_count == 1

    @staticmethod
    async def add_comment(post_id: str, comment: Comment, user_role: str) -> Optional[dict]:
        """게시글에 댓글을 추가 (별도 comment_collection에 저장)."""
        # 권한 체크
        if user_role not in ["admin", "user"]:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")

        # 게시글이 존재하는지 체크
        post = await post_collection.find_one({"_id": ObjectId(post_id)})
        if not post:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

        # 새 댓글 생성 -> comment_collection 에 insert
        comment_dict = comment.dict(by_alias=True)
        # post_id 추가 (어느 게시글의 댓글인지 구분 필요)
        comment_dict["post_id"] = ObjectId(post_id)

        result = await comment_collection.insert_one(comment_dict)
        if result.inserted_id:
            return {"comment_id": str(result.inserted_id)}
        return None

    @staticmethod
    async def delete_comment(post_id: str, comment_id: str, user_role: str, user_id: str) -> bool:
        """별도 comment_collection에서 삭제."""
        # 게시글 존재 확인
        post = await post_collection.find_one({"_id": ObjectId(post_id)})
        if not post:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

        # 실제 댓글 문서 조회
        c_doc = await comment_collection.find_one({"_id": ObjectId(comment_id), "post_id": ObjectId(post_id)})
        if not c_doc:
            raise HTTPException(status_code=404, detail="댓글을 찾을 수 없습니다.")

        if user_role != "admin" and c_doc["user_id"] != user_id:
            raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")

        result = await comment_collection.delete_one({"_id": ObjectId(comment_id), "post_id": ObjectId(post_id)})
        return result.deleted_count == 1
