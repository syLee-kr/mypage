from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from bson.errors import InvalidId

from app.database import db
from app.models.CalendarEvent import CalendarEvent

calendar_collection = db["calendar"]  # 주어진 컬렉션

class CalendarService:
    @staticmethod
    async def create_event(event: CalendarEvent) -> Optional[str]:
        """새로운 캘린더 이벤트 생성"""
        doc = event.dict(by_alias=True)
        result = await calendar_collection.insert_one(doc)
        if result.inserted_id:
            return str(result.inserted_id)
        return None

    @staticmethod
    async def get_events(
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
    ) -> List[CalendarEvent]:
        query = {}
        if start_date and end_date:
            query = {
                "start_date": {"$gte": start_date},
                "end_date": {"$lte": end_date}
            }
        elif start_date:
            query = {
                "start_date": {"$gte": start_date}
            }
        elif end_date:
            query = {
                "end_date": {"$lte": end_date}
            }

        # MongoDB에서 이벤트 조회 (예: Motor 사용)
        raw_events = await calendar_collection.find(query).to_list(length=100)

        # Pydantic 모델 인스턴스로 변환
        events = [CalendarEvent(**event) for event in raw_events]
        return events


    @staticmethod
    async def update_event(event_id: str, updated_data: dict) -> bool:
        """이벤트 수정"""
        oid = ObjectId(event_id)
        result = await calendar_collection.update_one(
            {"_id": oid},
            {"$set": updated_data}
        )
        return result.modified_count == 1

    @staticmethod
    async def delete_event(event_id: str) -> bool:
        try:
            oid = ObjectId(event_id)
        except InvalidId:
            print(f"Invalid ObjectId: {event_id}")
            return False
        result = await calendar_collection.delete_one({"_id": oid})
        return result.deleted_count == 1
