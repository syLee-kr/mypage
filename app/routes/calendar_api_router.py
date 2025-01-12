from fastapi import APIRouter, Request, HTTPException, Body, Query
from typing import List, Optional
from datetime import datetime
from starlette.responses import JSONResponse
from app.config.templates import templates
from app.service.CalendarService import CalendarService
from app.models.CalendarEvent import CalendarEvent
from app.service.UserService import UserService

router = APIRouter()

@router.get("")
async def calendar_page(request: Request):
    """
    달력 페이지를 렌더링하며 모든 이벤트 데이터를 제공합니다.
    """
    user_id = request.session.get("user_id")
    user_role = None
    if user_id:
        user_role = await UserService.check_user_role(user_id)

    # 이벤트 데이터 가져오기
    events = await CalendarService.get_events()

    if request.headers.get("accept") == "application/json":
        return JSONResponse(content={"events": events})
    print(f"User ID: {user_id}, User Role: {user_role}")

    # HTML 템플릿 렌더링
    return templates.TemplateResponse(
        "calendar.html",
        {
            "request": request,
            "user_role": user_role,
            "events": events,
        }
    )
@router.get("/events", response_model=List[CalendarEvent])
async def get_calendar_events(
        start: Optional[str] = Query(None),
        end: Optional[str] = Query(None),
):
    try:
        print(f"Received start: {start}, end: {end}")

        # 날짜 형식 변환
        try:
            start_date = datetime.fromisoformat(start) if start else None
            end_date = datetime.fromisoformat(end) if end else None
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

        print(f"Start Date: {start_date}, End Date: {end_date}")

        # CalendarService 호출
        events = await CalendarService.get_events(start_date=start_date, end_date=end_date)

        # 디버깅용 로그
        for event in events:
            print(f"Event ID: {event.id}")  # 각 이벤트의 ID를 로그로 출력

        return events  # Pydantic 모델을 통해 직렬화됨
    except Exception as e:
        print(f"Error while fetching events: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/create")
async def create_event(request: Request, payload: dict = Body(...)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    user_role = await UserService.check_user_role(user_id)
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    try:
        event = CalendarEvent(
            title=payload["title"],
            description=payload.get("description", ""),
            start_date=datetime.fromisoformat(payload["start_date"]),
            end_date=datetime.fromisoformat(payload["end_date"]),
            type=payload.get("type", "event")
        )
    except KeyError:
        raise HTTPException(status_code=400, detail="필수 필드가 누락되었습니다.")
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 잘못되었습니다.")

    event_id = await CalendarService.create_event(event)
    if not event_id:
        raise HTTPException(status_code=400, detail="이벤트 생성 실패")

    return {"message": "이벤트가 생성되었습니다.", "event_id": event_id}

@router.put("/{event_id}/edit")
async def update_event(request: Request, event_id: str, payload: dict = Body(...)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    user_role = await UserService.check_user_role(user_id)
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    updated_data = {}
    if "title" in payload:
        updated_data["title"] = payload["title"]
    if "description" in payload:
        updated_data["description"] = payload["description"]
    if "start_date" in payload:
        try:
            updated_data["start_date"] = datetime.fromisoformat(payload["start_date"])
        except ValueError:
            raise HTTPException(status_code=400, detail="start_date 형식이 잘못되었습니다.")
    if "end_date" in payload:
        try:
            updated_data["end_date"] = datetime.fromisoformat(payload["end_date"])
        except ValueError:
            raise HTTPException(status_code=400, detail="end_date 형식이 잘못되었습니다.")
    if "type" in payload:
        updated_data["type"] = payload["type"]

    success = await CalendarService.update_event(event_id, updated_data)
    if not success:
        raise HTTPException(status_code=400, detail="이벤트 수정 실패")

    return {"message": "이벤트가 수정되었습니다."}

@router.delete("/{event_id}")
async def delete_event(request: Request, event_id: str):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    user_role = await UserService.check_user_role(user_id)
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    success = await CalendarService.delete_event(event_id)
    if not success:
        raise HTTPException(status_code=400, detail="이벤트 삭제 실패")

    return {"message": "이벤트가 삭제되었습니다."}
