from datetime import datetime

from pydantic import BaseModel, Field


class AppointmentCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    notes: str | None = Field(default=None, max_length=600)
    scheduled_for: datetime


class AppointmentResponse(BaseModel):
    id: int
    couple_id: int
    creator_user_id: int
    title: str
    notes: str | None = None
    scheduled_for: datetime
    created_at: datetime


class AppointmentReminderResponse(BaseModel):
    id: int
    title: str
    notes: str | None = None
    scheduled_for: datetime
    days_until: int
