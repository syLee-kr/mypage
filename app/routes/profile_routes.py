from fastapi import APIRouter, Request, HTTPException
from starlette.responses import RedirectResponse

from app.config.templates import templates
from app.models.User import User
from app.service.UserService import UserService

router = APIRouter()

@router.get("")
async def get_profile(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    user_role = await UserService.check_user_role(user_id)

    # UserService를 사용하여 사용자 데이터 가져오기
    user: User = await UserService.find_user_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # 사용자 데이터를 사용하여 profile.html 템플릿 렌더링
    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "user_role": user_role})
