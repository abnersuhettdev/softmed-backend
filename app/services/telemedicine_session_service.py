from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.telemedicine_session import TelemedicineSession


class TelemedicineSessionService:
    @staticmethod
    def get_db_session() -> Session:
        """Get a database session. Caller is responsible for closing it."""
        return SessionLocal()

    def create_session(
        self,
        patient_id: int,
        doctor_id: int,
        meet_call_link: Optional[str] = None,
    ) -> TelemedicineSession:
        """Create a new telemedicine session."""
        db_session = self.get_db_session()
        try:
            session = TelemedicineSession(
                patient_id=patient_id,
                doctor_id=doctor_id,
                status="in_progress",
                meet_call_link=meet_call_link,
                started_at=datetime.utcnow(),
            )
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)
            return session
        except Exception as e:
            db_session.rollback()
            raise Exception(f"Failed to create telemedicine session: {e}") from e
        finally:
            db_session.close()

    def get_session(self, session_id: int) -> Optional[TelemedicineSession]:
        """Get a telemedicine session by ID."""
        db_session = self.get_db_session()
        try:
            return db_session.query(TelemedicineSession).filter(TelemedicineSession.id == session_id).first()
        finally:
            db_session.close()

    def get_active_session_by_patient(self, patient_id: int) -> Optional[TelemedicineSession]:
        """Get active telemedicine session for a patient."""
        db_session = self.get_db_session()
        try:
            return (
                db_session.query(TelemedicineSession)
                .filter(
                    TelemedicineSession.patient_id == patient_id,
                    TelemedicineSession.status == "in_progress",
                )
                .first()
            )
        finally:
            db_session.close()

    def get_active_sessions_by_doctor(self, doctor_id: int) -> List[TelemedicineSession]:
        """Get all active telemedicine sessions for a doctor."""
        db_session = self.get_db_session()
        try:
            return (
                db_session.query(TelemedicineSession)
                .filter(
                    TelemedicineSession.doctor_id == doctor_id,
                    TelemedicineSession.status == "in_progress",
                )
                .all()
            )
        finally:
            db_session.close()

    def get_all_active_sessions(self) -> List[TelemedicineSession]:
        """Get all active telemedicine sessions."""
        db_session = self.get_db_session()
        try:
            return db_session.query(TelemedicineSession).filter(TelemedicineSession.status == "in_progress").all()
        finally:
            db_session.close()

    def end_session(self, session_id: int, status: str = "completed", notes: Optional[str] = None) -> TelemedicineSession:
        """End a telemedicine session."""
        db_session = self.get_db_session()
        try:
            session = db_session.query(TelemedicineSession).filter(TelemedicineSession.id == session_id).first()
            if not session:
                raise Exception(f"Session {session_id} not found")
            session.status = status
            session.ended_at = datetime.utcnow()
            if notes:
                session.notes = notes
            db_session.commit()
            db_session.refresh(session)
            return session
        except Exception as e:
            db_session.rollback()
            raise Exception(f"Failed to end session: {e}") from e
        finally:
            db_session.close()

    def get_sessions(
        self,
        patient_id: Optional[int] = None,
        doctor_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[TelemedicineSession]:
        """Get telemedicine sessions with optional filters."""
        db_session = self.get_db_session()
        try:
            query = db_session.query(TelemedicineSession)
            if patient_id:
                query = query.filter(TelemedicineSession.patient_id == patient_id)
            if doctor_id:
                query = query.filter(TelemedicineSession.doctor_id == doctor_id)
            if status:
                query = query.filter(TelemedicineSession.status == status)
            return query.order_by(TelemedicineSession.started_at.desc()).all()
        finally:
            db_session.close()

