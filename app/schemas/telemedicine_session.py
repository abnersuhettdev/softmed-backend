from datetime import datetime

from pydantic import BaseModel


class TelemedicineSessionBase(BaseModel):
    patient_id: int
    doctor_id: int
    status: str = "in_progress"
    meet_call_link: str | None = None
    notes: str | None = None


class TelemedicineSessionCreate(TelemedicineSessionBase):
    pass


class TelemedicineSessionUpdate(BaseModel):
    status: str | None = None
    ended_at: datetime | None = None
    notes: str | None = None


class TelemedicineSession(TelemedicineSessionBase):
    id: int
    started_at: datetime
    ended_at: datetime | None = None

    class Config:
        from_attributes = True

