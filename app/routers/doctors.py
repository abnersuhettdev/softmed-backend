from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import Role, User as UserModel
from app.models.appointment import Appointment as AppointmentModel
from app.models.medical_record import MedicalRecord as MedicalRecordModel
from app.models.prescription import Prescription as PrescriptionModel
from app.models.telemedicine_session import TelemedicineSession as TelemedicineSessionModel
from app.models.payment import Payment as PaymentModel
from app.models.announcement import AnnouncementRead as AnnouncementReadModel, Announcement as AnnouncementModel
from app.schemas import user as user_schema
from app.routers.users import get_password_hash, get_current_user


class TelemedicineAccessUpdate(BaseModel):
    enabled: bool

router = APIRouter()


@router.post("/", response_model=user_schema.User)
def create_doctor(
    user: user_schema.UserCreate, db: Session = Depends(get_db)
):
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    
    # Exclude password and role from user.dict() since we handle them separately
    user_data = user.dict(exclude={'password', 'role'})
    db_user = UserModel(
        **user_data,
        hashed_password=hashed_password,
        role=Role.DOCTOR,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/", response_model=List[user_schema.User])
def read_doctors(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    specialty: Optional[str] = Query(None, description="Filter by primary specialty"),
    db: Session = Depends(get_db)
):
    query = db.query(UserModel).filter(UserModel.role == Role.DOCTOR)
    
    if specialty:
        query = query.filter(UserModel.primary_specialty == specialty)
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/{doctor_id}", response_model=user_schema.User)
def read_doctor(doctor_id: int, db: Session = Depends(get_db)):
    db_user = (
        db.query(UserModel)
        .filter(UserModel.id == doctor_id, UserModel.role == Role.DOCTOR)
        .first()
    )
    if db_user is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db_user


@router.put("/{doctor_id}", response_model=user_schema.User)
def update_doctor(
    doctor_id: int,
    user: user_schema.UserCreate,
    db: Session = Depends(get_db),
):
    db_user = (
        db.query(UserModel)
        .filter(UserModel.id == doctor_id, UserModel.role == Role.DOCTOR)
        .first()
    )
    if db_user is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    user_data = user.dict(exclude_unset=True)
    for key, value in user_data.items():
        setattr(db_user, key, value)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor(
    doctor_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently delete a doctor from the database.
    Only admins and superadmins can delete doctors.
    This will also delete related records (appointments, medical records, etc.)
    if foreign key constraints allow cascade deletion.
    """
    # Check if current user is admin or superadmin
    if current_user.role not in [Role.ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete doctors"
        )
    
    db_user = (
        db.query(UserModel)
        .filter(UserModel.id == doctor_id, UserModel.role == Role.DOCTOR)
        .first()
    )
    if db_user is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Prevent self-deletion
    if db_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    try:
        doctor_id = db_user.id
        
        # Delete all related records before deleting the doctor
        # 1. Delete appointments where doctor is patient or doctor
        db.query(AppointmentModel).filter(
            (AppointmentModel.patient_id == doctor_id) | 
            (AppointmentModel.doctor_id == doctor_id)
        ).delete()
        
        # 2. Delete medical records where doctor is patient or doctor
        db.query(MedicalRecordModel).filter(
            (MedicalRecordModel.patient_id == doctor_id) | 
            (MedicalRecordModel.doctor_id == doctor_id)
        ).delete()
        
        # 3. Delete prescriptions where doctor is patient or prescriber
        db.query(PrescriptionModel).filter(
            (PrescriptionModel.patient_id == doctor_id) | 
            (PrescriptionModel.prescriber_id == doctor_id)
        ).delete()
        
        # 4. Delete telemedicine sessions where doctor is patient or doctor
        db.query(TelemedicineSessionModel).filter(
            (TelemedicineSessionModel.patient_id == doctor_id) | 
            (TelemedicineSessionModel.doctor_id == doctor_id)
        ).delete()
        
        # 5. Delete payments for the doctor
        db.query(PaymentModel).filter(PaymentModel.user_id == doctor_id).delete()
        
        # 6. Delete announcement reads for the doctor
        db.query(AnnouncementReadModel).filter(AnnouncementReadModel.user_id == doctor_id).delete()
        
        # 7. Handle announcements created by the doctor (set created_by_id to NULL or delete)
        # Option: Set created_by_id to NULL to preserve announcements
        # Or delete announcements created by this doctor
        # For now, we'll delete announcements created by this doctor
        db.query(AnnouncementModel).filter(AnnouncementModel.created_by_id == doctor_id).delete()
        
        # 8. Handle announcements where doctor is recipient (set recipient_id to NULL)
        # Since recipient_id is nullable, we can set it to NULL
        db.query(AnnouncementModel).filter(AnnouncementModel.recipient_id == doctor_id).update({AnnouncementModel.recipient_id: None})
        
        # Now delete the doctor
        db.delete(db_user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete doctor: {str(e)}"
        )
    return


@router.put("/{doctor_id}/queue/open", status_code=status.HTTP_200_OK)
def open_doctor_queue(doctor_id: int, db: Session = Depends(get_db)):
    """Open a doctor's queue for telemedicine."""
    db_user = (
        db.query(UserModel)
        .filter(UserModel.id == doctor_id, UserModel.role == Role.DOCTOR)
        .first()
    )
    if db_user is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Check requirements for opening queue
    # 1. Admin must have enabled telemedicine_access (admin-controlled flag)
    if not db_user.telemedicine_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor does not have telemedicine access. Please contact administrator.",
        )
    
    # 2. Doctor must have completed their profile
    if not db_user.profile_completed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please complete your profile before opening the queue.",
        )
    
    # 3. Doctor must have Google Calendar enabled (required for Google Meet links)
    if not db_user.google_calendar_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google Calendar must be connected to use telemedicine. Please reconnect your Google account.",
        )
    
    db_user.queue_open = True
    db.commit()
    db.refresh(db_user)
    return {"message": f"Doctor {doctor_id} queue opened", "queue_open": True}


@router.put("/{doctor_id}/queue/close", status_code=status.HTTP_200_OK)
def close_doctor_queue(doctor_id: int, db: Session = Depends(get_db)):
    """Close a doctor's queue for telemedicine."""
    db_user = (
        db.query(UserModel)
        .filter(UserModel.id == doctor_id, UserModel.role == Role.DOCTOR)
        .first()
    )
    if db_user is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    db_user.queue_open = False
    db.commit()
    db.refresh(db_user)
    return {"message": f"Doctor {doctor_id} queue closed", "queue_open": False}


@router.put("/{doctor_id}/telemedicine-access", status_code=status.HTTP_200_OK)
def update_doctor_telemedicine_access(
    doctor_id: int,
    update: TelemedicineAccessUpdate,
    db: Session = Depends(get_db)
):
    """Update a doctor's telemedicine access."""
    db_user = (
        db.query(UserModel)
        .filter(UserModel.id == doctor_id, UserModel.role == Role.DOCTOR)
        .first()
    )
    if db_user is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    db_user.telemedicine_access = update.enabled
    # If disabling telemedicine access, also close the queue
    if not update.enabled:
        db_user.queue_open = False
    db.commit()
    db.refresh(db_user)
    return {
        "message": f"Doctor {doctor_id} telemedicine access {'enabled' if update.enabled else 'disabled'}",
        "telemedicine_access": update.enabled,
        "queue_open": db_user.queue_open or False,
    }


@router.get("/{doctor_id}/queue/status")
def get_doctor_queue_status(doctor_id: int, db: Session = Depends(get_db)):
    """Get a doctor's queue status."""
    db_user = (
        db.query(UserModel)
        .filter(UserModel.id == doctor_id, UserModel.role == Role.DOCTOR)
        .first()
    )
    if db_user is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return {
        "doctor_id": doctor_id,
        "queue_open": db_user.queue_open or False,
        "telemedicine_access": db_user.telemedicine_access or False,
    }


@router.post("/me/complete-profile", response_model=user_schema.User)
def complete_profile(
    profile_data: user_schema.DoctorProfileCompletion,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Complete doctor profile after Google OAuth signup.
    Updates profile information and sets profile_completed=True.
    """
    # Verify user is a doctor
    if current_user.role != Role.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can complete profile"
        )
    
    # Fetch user in current session to avoid session conflicts
    doctor = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )
    
    # Update profile fields (only provided fields)
    profile_dict = profile_data.dict(exclude_unset=True)
    
    for key, value in profile_dict.items():
        if value is not None:  # Only update non-None values
            setattr(doctor, key, value)
    
    # Mark profile as completed
    doctor.profile_completed = True
    
    # Auto-enable telemedicine_access when profile is completed and Google Calendar is enabled
    # This allows doctors to use telemedicine immediately after completing their profile
    if doctor.google_calendar_enabled:
        doctor.telemedicine_access = True
        print(f"[complete_profile] Auto-enabled telemedicine_access for doctor {doctor.id} (Google Calendar enabled)")
    
    # Commit the changes
    db.commit()
    db.refresh(doctor)
    
    # Return doctor with all fields including profile_completed
    # The response_model will serialize it according to User schema
    return doctor
