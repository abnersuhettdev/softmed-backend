from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    pix_transaction_id = Column(String, nullable=True)
    pix_qr_code_data = Column(String, nullable=True)
    pix_status = Column(String, default="pending", nullable=False)

    user = relationship("User", back_populates="payments")
