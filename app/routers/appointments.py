from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.appointment import Appointment as AppointmentModel
from app.schemas.appointment import Appointment as AppointmentSchema, AppointmentCreate
from app.schemas.appointment import CreateMeetingRequest
from app.services.google_meet_service import GoogleMeetService
from app.routers.users import get_current_user
from app.models.user import User as UserModel

router = APIRouter()


@router.get("/", response_model=List[AppointmentSchema])
def get_appointments(
    doctor_id: Optional[int] = Query(None, description="Filter by doctor ID"),
    patient_id: Optional[int] = Query(None, description="Filter by patient ID"),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get appointments with optional filtering.
    """
    query = db.query(AppointmentModel)
    
    if doctor_id:
        query = query.filter(AppointmentModel.doctor_id == doctor_id)
    if patient_id:
        query = query.filter(AppointmentModel.patient_id == patient_id)
    if date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(
                db.func.date(AppointmentModel.appointment_time) == date_obj
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    appointments = query.order_by(AppointmentModel.appointment_time).all()
    return appointments


@router.get("/availability/{doctor_id}")
def get_doctor_availability(
    doctor_id: int,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """
    Get available time slots for a doctor on a specific date.
    Returns available time slots and booked appointments.
    """
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get all appointments for this doctor on this date
    appointments = (
        db.query(AppointmentModel)
        .filter(
            AppointmentModel.doctor_id == doctor_id,
            db.func.date(AppointmentModel.appointment_time) == date_obj,
            AppointmentModel.status.in_(["scheduled", "in_progress"])
        )
        .order_by(AppointmentModel.appointment_time)
        .all()
    )
    
    # Generate all possible time slots (30-minute intervals from 8:00 to 18:00)
    time_slots = []
    start_time = datetime.combine(date_obj, datetime.min.time().replace(hour=8, minute=0))
    end_time = datetime.combine(date_obj, datetime.min.time().replace(hour=18, minute=0))
    
    current_time = start_time
    while current_time < end_time:
        slot_end = current_time + timedelta(minutes=30)
        if slot_end <= end_time:
            # Check if this slot is booked
            is_booked = any(
                apt.appointment_time <= current_time < apt.appointment_time + timedelta(minutes=30) or
                apt.appointment_time < slot_end <= apt.appointment_time + timedelta(minutes=30)
                for apt in appointments
            )
            
            time_slots.append({
                "time": current_time.strftime("%H:%M"),
                "datetime": current_time.isoformat(),
                "available": not is_booked,
                "status": "booked" if is_booked else "available"
            })
        
        current_time += timedelta(minutes=30)
    
    return {
        "doctor_id": doctor_id,
        "date": date,
        "time_slots": time_slots,
        "booked_count": len(appointments),
        "available_count": len([s for s in time_slots if s["available"]])
    }


@router.post("/", response_model=AppointmentSchema)
def create_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new appointment.
    Checks for conflicts before creating.
    """
    # Check for existing appointment at the same time
    appointment_time = appointment.appointment_time
    existing = (
        db.query(AppointmentModel)
        .filter(
            AppointmentModel.doctor_id == appointment.doctor_id,
            AppointmentModel.appointment_time == appointment_time,
            AppointmentModel.status.in_(["scheduled", "in_progress"])
        )
        .first()
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This time slot is already booked. Please select another time."
        )
    
    # Check if appointment is in the past
    if appointment_time < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book appointments in the past"
        )
    
    db_appointment = AppointmentModel(
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        appointment_time=appointment.appointment_time,
        status=appointment.status or "scheduled"
    )
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment


@router.post("/create-meeting")
def create_meeting(
    request: CreateMeetingRequest,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a Google Meet link for an appointment.
    Requires the current user to be a doctor with Google Calendar connected.
    """
    # Verify user is a doctor
    if current_user.role != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can create meetings"
        )
    
    try:
        # Create GoogleMeetService with doctor's credentials
        meet_service = GoogleMeetService(doctor_id=current_user.id, db=db)
        meet_link = meet_service.create_meeting(
            summary=request.summary,
            start_time=request.start_time,
            end_time=request.end_time,
            attendees=request.attendees
        )
        return {"meet_link": meet_link}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Google Meet meeting: {e}",
        )
