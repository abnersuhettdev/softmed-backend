import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, ForeignKey, Enum as EnumDB
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship

from app.database import Base


class AnnouncementType(str, enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class Announcement(Base):
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    message = Column(Text, nullable=False)
    # Use PostgreSQL ENUM type directly with create_type=False to avoid auto-creation
    type = Column(postgresql.ENUM('info', 'success', 'warning', 'error', name='announcementtype', create_type=False), default='info', nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # None = broadcast to all
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to creator (admin)
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    # Relationship to recipient (if specific user)
    recipient = relationship("User", foreign_keys=[recipient_id])


class AnnouncementRead(Base):
    __tablename__ = "announcement_reads"

    id = Column(Integer, primary_key=True, index=True)
    announcement_id = Column(Integer, ForeignKey("announcements.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    read_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    announcement = relationship("Announcement")
    user = relationship("User")
