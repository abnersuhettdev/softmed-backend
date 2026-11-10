from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class TelemedicineSession(Base):
    __tablename__ = "telemedicine_sessions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    status = Column(
        String,
        default="in_progress",
        nullable=False,
        index=True,
    )  # 'in_progress', 'completed', 'cancelled', 'abandoned'
    meet_call_link = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    patient = relationship("User", foreign_keys=[patient_id], back_populates="telemedicine_sessions_as_patient")
    doctor = relationship("User", foreign_keys=[doctor_id], back_populates="telemedicine_sessions_as_doctor")

