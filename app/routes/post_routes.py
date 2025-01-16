from fastapi import APIRouter, Request, Form, HTTPException, UploadFile, File, Body
from typing import Optional, List
from datetime import datetime
import os

from app.config.templates import templates
from app.service.PostService import PostService
from app.service.UserService import UserService
from app.models.Comment import Comment

router = APIRouter()

@router.get("")
async def post_list(
        request: Request,
        limit: int = 10,
        skip: int = 0,
        format: Optional[str] = None,
):
    user_id = request.session.get("user_id")

    if not user_id:
        user_role = None
    else:
        user_role = await UserService.check_user_role(user_id)

    posts = await PostService.get_posts(skip=skip, limit=limit)

    if format == "json":
        # JSON 형태로 게시글 목록 반환 (무한 스크롤)
        post_dicts = []
        for p in posts:
            post_dicts.append({
                "id": str(p.id),
                "author_id": p.author_id,
                "content": p.content,
                "is_public": p.is_public,
                "image_urls": p.image_urls,
                "likes": p.likes,
                "comments": [c.dict(by_alias=True) for c in p.comments],
                "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            })
        return {"posts": post_dicts}
    else:
        # HTML 템플릿 렌더링
        return templates.TemplateResponse(
            "post_list.html",
            {
                "request": request,
                "initial_posts": posts,  # 2개 댓글만 포함된 게시글 목록
                "user_id": user_id,
                "user_role": user_role,
            },
        )

@router.get("/{post_id}")
async def post_detail(
        request: Request,
        post_id: str,
        format: Optional[str] = None,
):
    """
    게시글 상세:
    - PostService.get_post_details()에서 해당 게시글의 모든 댓글을 가져옴
    - post_detail.html을 렌더링 (또는 JSON)
    """
    user_id = request.session.get("user_id")

    if not user_id:
        user_role = None
    else:
        user_role = await UserService.check_user_role(user_id)

    updated_post = await PostService.get_post_details(post_id)
    if not updated_post:
        raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")

    if format == "json":
        # 상세 정보 JSON으로 반환할 경우
        return {
            "id": str(updated_post.id),
            "author_id": updated_post.author_id,
            "content": updated_post.content,
            "is_public": updated_post.is_public,
            "image_urls": updated_post.image_urls,
            "likes": updated_post.likes,
            # 모든 댓글
            "comments": [c.dict(by_alias=True) for c in updated_post.comments],
            "timestamp": updated_post.timestamp.strftime("%Y-%m-%d %H:%M") if updated_post.timestamp else None,
        }
    else:
        # HTML 템플릿 예: post_detail.html
        return templates.TemplateResponse(
            "post_detail.html",
            {
                "request": request,
                "post": updated_post,  # 전체 댓글 포함
                "user_id": user_id,
                "user_role": user_role,
            },
        )


@router.post("/create")
async def create_post(
        request: Request,
        content: str = Form(...),
        is_public: bool = Form(...),
        images: List[UploadFile] = File([]),
):
    """
    게시글 생성 (관리자만)
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    user = await UserService.find_user_by_user_id(user_id)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    # 이미지 처리
    image_urls = []
    for img in images:
        if img.content_type.startswith("image/"):
            save_dir = "app/static/post/"
            os.makedirs(save_dir, exist_ok=True)
            file_location = os.path.join(save_dir, img.filename)
            with open(file_location, "wb+") as f:
                f.write(await img.read())
            image_urls.append(f"/static/post/{img.filename}")

    # 새 게시글 데이터 구성
    new_post = {
        "author_id": user_id,
        "content": content,
        "is_public": is_public,
        "image_urls": image_urls,
        "likes": [],
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
    }

    created_post = await PostService.create_post(new_post, user.role)
    if not created_post:
        raise HTTPException(status_code=400, detail="게시글 작성 실패")

    return {"message": "게시글이 작성되었습니다.", "post": created_post}


@router.put("/{post_id}/edit")
async def edit_post(
        post_id: str,
        request: Request,
        content: str = Form(...),
        is_public: bool = Form(...),
        image: Optional[UploadFile] = File(None),
):
    """
    게시글 수정 (관리자만)
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    user = await UserService.find_user_by_user_id(user_id)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    image_url = None
    if image:
        save_dir = "app/static/post/"
        os.makedirs(save_dir, exist_ok=True)
        file_location = os.path.join(save_dir, image.filename)
        with open(file_location, "wb+") as file_object:
            file_object.write(await image.read())
        image_url = f"/static/post/{image.filename}"

    updated_fields = {
        "content": content,
        "is_public": is_public,
    }
    if image_url:
        updated_fields["image_urls"] = [image_url]

    success = await PostService.update_post(post_id, updated_fields)
    if not success:
        raise HTTPException(status_code=400, detail="게시글 수정 실패")
    return {"message": "게시글이 수정되었습니다.", "post": success}


@router.delete("/{post_id}")
async def delete_post(post_id: str, request: Request):
    """
    게시글 삭제 (관리자 or 본인)
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    user = await UserService.find_user_by_user_id(user_id)

    success = await PostService.delete_post(post_id, user.role, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="게시글 삭제 실패")

    return {"message": "게시글이 삭제되었습니다."}


# 좋아요, 댓글 작성/삭제 로직은 기존과 동일
@router.post("/{post_id}/like")
async def toggle_like(post_id: str, request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    success = await PostService.like_post(post_id, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="좋아요 토글 실패")

    updated_post = await PostService.get_post_details(post_id)
    if not updated_post:
        raise HTTPException(status_code=404, detail="업데이트된 게시글을 찾을 수 없습니다.")

    # 직렬화
    post_dict = {
        "id": str(updated_post.id),
        "author_id": str(updated_post.author_id),
        "content": updated_post.content,
        "is_public": updated_post.is_public,
        "image_urls": updated_post.image_urls,
        "likes": [str(like) for like in updated_post.likes],
        "comments": [
            {
                "id": str(c.id),
                "user_id": str(c.user_id),
                "post_id": str(c.post_id),  # 여기에 post_id 추가
                "content": c.content,
                "timestamp": c.timestamp.strftime("%Y-%m-%d %H:%M") if c.timestamp else None
            }
            for c in updated_post.comments
        ],
        "timestamp": updated_post.timestamp.strftime("%Y-%m-%d %H:%M") if updated_post.timestamp else None,
    }

    return {"message": "좋아요 상태가 변경되었습니다.", "post": post_dict}


@router.post("/{post_id}/comments")
async def add_comment(post_id: str, request: Request, payload: dict = Body(...)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    user = await UserService.find_user_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    content = payload.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="댓글 내용이 없습니다.")

    if user.role not in ["admin", "user"]:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    new_comment = Comment(user_id=user_id, content=content, post_id=post_id)
    result = await PostService.add_comment(post_id, new_comment, user.role)
    if not result:
        raise HTTPException(status_code=400, detail="댓글 추가 실패")

    # 추가된 댓글 데이터를 반환
    return {
        "message": "댓글이 추가되었습니다.",
        "comment_id": result["comment_id"],
        "user_id": user_id,
        "content": content,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),  # UTC로 반환
    }


@router.delete("/{post_id}/comments/{comment_id}")
async def delete_comment(post_id: str, comment_id: str, request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    user = await UserService.find_user_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    success = await PostService.delete_comment(post_id, comment_id, user.role, user_id)
    if not success:
        raise HTTPException(status_code=400, detail="댓글 삭제 실패")

    return {"message": "댓글이 삭제되었습니다."}
