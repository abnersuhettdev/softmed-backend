from datetime import datetime

from pydantic import BaseModel


class SettingsBase(BaseModel):
    key: str
    value: str


class SettingsCreate(SettingsBase):
    updated_by: int | None = None


class SettingsUpdate(BaseModel):
    value: str
    updated_by: int | None = None


class Settings(SettingsBase):
    id: int
    updated_at: datetime | None = None
    updated_by: int | None = None

    class Config:
        from_attributes = True

