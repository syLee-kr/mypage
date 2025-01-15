from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from app.config.templates import templates
from app.service.UserService import UserService

router = APIRouter()


@router.get("")
async def login_page(request: Request):
    user_session = request.session.get("user")
    if user_session:
        return RedirectResponse(url="/post", status_code=302)
    return templates.TemplateResponse("login/login.html", {"request": request})


@router.post("")
async def login(
        request: Request,
        userId: str = Form(...),
        password: str = Form(...),
):
    # 1. DB에서 사용자 정보 조회 (아이디로 검색)
    user_db = await UserService.is_user_id_duplicate(userId)
    if not user_db:
        return templates.TemplateResponse(
            "login/login.html",
            {
                "request": request,
                "loginFail": True,
                "errorMessage": "존재하지 않는 사용자입니다."
            }
        )

    # 2. 사용자 인증 (비밀번호 일치 여부 검증)
    is_valid_user = await UserService.verify_user_credentials(userId, password)
    if is_valid_user:
        user = await UserService.find_user_by_user_id(userId)  # await 추가
        # 3. 세션에 사용자 정보 저장 (user_id, role)
        request.session["user_id"] = user.user_id
        request.session["user_role"] = user.role
        print(f"Session user_id: {request.session.get('user_id')}")
        return RedirectResponse(url="/post", status_code=302)

    # 4. 로그인 실패 시 에러 메시지와 함께 페이지 렌더링
    return templates.TemplateResponse(
        "login/login.html",
        {
            "request": request,
            "loginFail": True,
            "errorMessage": "아이디 또는 비밀번호가 잘못되었습니다."
        }
    )


@router.get("/logout")
def logout(request: Request):
    if "user_id" in request.session:
        del request.session["user_id"]
    if "user_role" in request.session:
        del request.session["user_role"]

    # 로그인 페이지로 리다이렉트
    return RedirectResponse(url="/login", status_code=302)
