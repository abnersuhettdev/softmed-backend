from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.announcement import AnnouncementType


class AnnouncementBase(BaseModel):
    title: str
    message: str
    type: AnnouncementType = AnnouncementType.INFO
    recipient_id: Optional[int] = None  # None = broadcast to all users


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    type: Optional[AnnouncementType] = None
    recipient_id: Optional[int] = None  # None = broadcast to all users


class Announcement(AnnouncementBase):
    id: int
    created_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AnnouncementWithReadStatus(Announcement):
    read: bool
    read_at: Optional[datetime] = None


class FeedbackCreate(BaseModel):
    message: str

