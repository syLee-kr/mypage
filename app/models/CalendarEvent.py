from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from bson import ObjectId

from app.config.pyobjectid import PyObjectId

class CalendarEvent(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    type: Optional[str] = "event"

    model_config = {
        'populate_by_name': True,      # Pydantic v2 키
        'from_attributes': True,       # Pydantic v2 키
        'arbitrary_types_allowed': True,
        'json_encoders': {ObjectId: str},
    }
