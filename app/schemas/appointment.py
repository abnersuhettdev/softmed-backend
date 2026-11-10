from datetime import datetime
from typing import List

from pydantic import BaseModel

from app.schemas.user import User


class AppointmentBase(BaseModel):
    appointment_time: datetime
    status: str = "scheduled"


class AppointmentCreate(AppointmentBase):
    patient_id: int
    doctor_id: int


class Appointment(AppointmentBase):
    id: int
    patient: User
    doctor: User

    class Config:
        from_attributes = True


class CreateMeetingRequest(BaseModel):
    summary: str
    start_time: datetime
    end_time: datetime
    attendees: List[str] = []
