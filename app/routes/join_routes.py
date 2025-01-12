# app/routers/join_router.py

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from app.config.templates import templates
from app.models.User import User
from app.service.UserService import UserService

router = APIRouter()

@router.get("")
async def join_page(request: Request):
    user_session = request.session.get("user_id")  # 세션 키 수정
    if user_session:
        return RedirectResponse(url="/post", status_code=302)
    return templates.TemplateResponse("login/join.html", {"request": request})

@router.post("")
async def join(
        request: Request,
        user_id: str = Form(...),
        password: str = Form(...),
        name: str = Form(...),
        phone: str = Form(...),
        birthday: str = Form(...),
        profile_image: str = Form(default="profile.png"),
):
    """
    회원가입 처리
    """
    # 사용자 중복 체크
    if await UserService.is_user_id_duplicate(user_id):
        return templates.TemplateResponse(
            "join.html",
            {
                "request": request,
                "joinFail": True,
                "errorMessage": "이미 존재하는 아이디입니다.",
            },
        )

    # 새로운 사용자 생성
    new_user = User(
        user_id=user_id,
        password=password,
        name=name,
        phone=phone,
        birthday=birthday,
        profile_image=profile_image,
        role="user"
    )
    result = await UserService.create_user(new_user)

    if result:
        return RedirectResponse(url="/login", status_code=302)
    else:
        return templates.TemplateResponse(
            "join.html",
            {
                "request": request,
                "joinFail": True,
                "errorMessage": "사용자 생성에 실패했습니다.",
            },
        )
