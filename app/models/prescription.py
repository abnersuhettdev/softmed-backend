from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.user import User


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    prescriber_id = Column(Integer, ForeignKey("users.id"))
    prescription_date = Column(DateTime, default=datetime.utcnow)
    medication = Column(String)
    dosage = Column(String)

    patient = relationship(
        "User", foreign_keys=[patient_id], back_populates="prescriptions"
    )
    prescriber = relationship(
        "User",
        foreign_keys=[prescriber_id],
        back_populates="prescriptions_as_prescriber",
    )
