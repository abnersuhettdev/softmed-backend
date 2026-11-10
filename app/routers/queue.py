from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.queue_service import QueueService
from app.services.settings_service import SettingsService

router = APIRouter()


@router.get("/availability")
def check_queue_availability(queue_service: QueueService = Depends(), db: Session = Depends(get_db)):
    """Check if queue is available for patients to join."""
    try:
        is_available = queue_service.is_queue_available()
        reason = None
        if not is_available:
            settings_service = SettingsService(db)
            if not settings_service.is_telemedicine_enabled():
                reason = "Telemedicine is disabled by administrator"
            else:
                doctors = queue_service.get_doctors_with_open_queue()
                if len(doctors) == 0:
                    reason = "No doctors available with open queue"
        return {
            "available": is_available,
            "reason": reason,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check queue availability: {e}",
        )


@router.post("/{patient_id}")
def add_to_queue(patient_id: int, queue_service: QueueService = Depends(), db: Session = Depends(get_db)):
    try:
        # Check if queue is available before allowing join
        if not queue_service.is_queue_available():
            settings_service = SettingsService(db)
            if not settings_service.is_telemedicine_enabled():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Telemedicine queue is currently disabled by administrator",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No doctors available with open queue at the moment",
                )
        queue_service.add_to_queue(patient_id)
        return {"message": f"Patient {patient_id} added to the queue."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add patient to queue: {e}",
        )


@router.delete("/{patient_id}")
def remove_from_queue(patient_id: int, queue_service: QueueService = Depends()):
    try:
        queue_service.remove_from_queue(patient_id)
        return {"message": f"Patient {patient_id} removed from the queue."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove patient from queue: {e}",
        )


@router.get("/")
def get_queue(queue_service: QueueService = Depends()):
    """
    Get queue with patient details including queue_entry_time.
    Returns list of patient objects with id, name, queue_entry_time.
    """
    try:
        return queue_service.get_queue_with_details()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve queue: {e}",
        )


@router.post("/call_next/{doctor_id}", status_code=status.HTTP_200_OK)
def call_next_patient(doctor_id: int, queue_service: QueueService = Depends()):
    try:
        # The call_next_patient method in QueueService handles updating DB and Redis, creating Appointment, and generating meet link.
        result = queue_service.call_next_patient(doctor_id=doctor_id)
        return result
    except HTTPException as e:
        # Re-raise HTTPException to preserve status code and detail
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to call next patient: {e}",
        )


@router.get("/stats")
def get_queue_stats(queue_service: QueueService = Depends()):
    try:
        return queue_service.get_queue_stats()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve queue stats: {e}",
        )


@router.get("/status/{patient_id}")
def get_queue_status(patient_id: int, queue_service: QueueService = Depends()):
    """
    Get queue status for a specific patient.
    Returns position in queue and estimated wait time.
    """
    try:
        queue_list = queue_service.get_queue_with_details()
        patient_in_queue = any(p.get('id') == patient_id for p in queue_list)
        
        if not patient_in_queue:
            return {
                "position": 0,
                "is_in_queue": False,
                "estimated_wait_time": None
            }
        
        # Find patient position (1-based)
        position = next((i + 1 for i, p in enumerate(queue_list) if p.get('id') == patient_id), 0)
        
        # Estimate wait time: ~15 minutes per patient ahead
        estimated_wait_time = (position - 1) * 15 if position > 0 else 0
        
        return {
            "position": position,
            "is_in_queue": True,
            "estimated_wait_time": estimated_wait_time
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve queue status: {e}",
        )
