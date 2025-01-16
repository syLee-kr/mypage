from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

router = APIRouter()

@router.get("")
async def wait():
    error_message = "현재 페이지는 구현 중입니다."
    return RedirectResponse(url=f"/post?errorMessage={error_message}")