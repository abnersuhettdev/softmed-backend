from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.telemedicine_session import TelemedicineSession, TelemedicineSessionUpdate
from app.services.telemedicine_session_service import TelemedicineSessionService

router = APIRouter()


@router.get("/", response_model=List[TelemedicineSession])
def get_sessions(
    patient_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    status: Optional[str] = None,
    session_service: TelemedicineSessionService = Depends(),
):
    """Get telemedicine sessions with optional filters."""
    try:
        sessions = session_service.get_sessions(patient_id=patient_id, doctor_id=doctor_id, status=status)
        return sessions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sessions: {e}",
        )


@router.get("/{session_id}", response_model=TelemedicineSession)
def get_session(session_id: int, session_service: TelemedicineSessionService = Depends()):
    """Get a telemedicine session by ID."""
    try:
        session = session_service.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session: {e}",
        )


@router.get("/patient/{patient_id}/active", response_model=Optional[TelemedicineSession])
def get_active_session_by_patient(patient_id: int, session_service: TelemedicineSessionService = Depends()):
    """Get active telemedicine session for a patient."""
    try:
        session = session_service.get_active_session_by_patient(patient_id)
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve active session: {e}",
        )


@router.put("/{session_id}/end", response_model=TelemedicineSession)
def end_session(
    session_id: int,
    session_update: TelemedicineSessionUpdate,
    session_service: TelemedicineSessionService = Depends(),
):
    """End a telemedicine session."""
    try:
        status_value = session_update.status or "completed"
        session = session_service.end_session(session_id, status=status_value, notes=session_update.notes)
        return session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {e}",
        )

