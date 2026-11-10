from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os

from app.database import get_db
from app.models.user import User as UserModel
from app.models.medical_record import MedicalRecord as MedicalRecordModel
from app.models.telemedicine_session import TelemedicineSession as TelemedicineSessionModel
from app.models.appointment import Appointment as AppointmentModel
from app.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordUpdate,
    MedicalRecordResponse,
    MedicalRecordSignRequest,
    MedicalRecordPrescriptionRequest,
    MedicationItem,
    MedicalRecord,  # Legacy schema
)
from app.routers.users import get_current_user
from app.models.user import Role
from app.services.medical_record_encryption_service import MedicalRecordEncryptionService
from app.services.vidaas_service import VidaasService
from app.services.mevo_service import MevoService

router = APIRouter()


def _decrypt_medical_record(record: MedicalRecordModel) -> str | None:
    """Helper function to decrypt medical record"""
    if not record.encrypted_data or not record.encryption_iv or not record.encryption_auth_tag:
        return None
    
    try:
        encryption_service = MedicalRecordEncryptionService()
        return encryption_service.decrypt(
            record.encrypted_data,
            record.encryption_iv,
            record.encryption_auth_tag
        )
    except Exception as e:
        print(f"Error decrypting medical record {record.id}: {e}")
        return None


def _check_consultation_active(record: MedicalRecordModel, db: Session) -> bool:
    """Check if consultation/session is still active (not finished)"""
    if record.session_id:
        session = db.query(TelemedicineSessionModel).filter(
            TelemedicineSessionModel.id == record.session_id
        ).first()
        if session and session.status == "in_progress":
            return True
    return False


@router.post("/", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
def create_medical_record(
    record_data: MedicalRecordCreate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new medical record (encrypted).
    Only doctors can create medical records during active consultation.
    """
    if current_user.role != Role.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can create medical records"
        )
    
    # Verify patient exists
    patient = db.query(UserModel).filter(UserModel.id == record_data.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Verify consultation/session is active (if session_id provided)
    if record_data.session_id:
        session = db.query(TelemedicineSessionModel).filter(
            TelemedicineSessionModel.id == record_data.session_id,
            TelemedicineSessionModel.doctor_id == current_user.id,
            TelemedicineSessionModel.status == "in_progress"
        ).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session not found or not active"
            )
    
    # Encrypt medical record
    encryption_service = MedicalRecordEncryptionService()
    encrypted_data = encryption_service.encrypt(record_data.medical_record_text)
    
    # Create medical record
    medical_record = MedicalRecordModel(
        patient_id=record_data.patient_id,
        doctor_id=current_user.id,
        session_id=record_data.session_id,
        consultation_id=record_data.consultation_id,
        encrypted_data=encrypted_data["encryptedData"],
        encryption_iv=encrypted_data["iv"],
        encryption_auth_tag=encrypted_data["authTag"],
        is_signed=False,
    )
    
    db.add(medical_record)
    db.commit()
    db.refresh(medical_record)
    
    # Load patient relationship
    _ = medical_record.patient
    
    # Decrypt for response (doctor created it, so they can see it)
    decrypted_text = _decrypt_medical_record(medical_record)
    
    return MedicalRecordResponse(
        id=medical_record.id,
        patient_id=medical_record.patient_id,
        doctor_id=medical_record.doctor_id,
        session_id=medical_record.session_id,
        consultation_id=medical_record.consultation_id,
        record_date=medical_record.record_date,
        medical_record_text=decrypted_text,
        is_signed=medical_record.is_signed,
        signed_at=medical_record.signed_at,
        signature_id=medical_record.signature_id,
        signed_hash=medical_record.signed_hash,
        vidaas_certificate_id=medical_record.vidaas_certificate_id,
        vidaas_user_id=medical_record.vidaas_user_id,
        signature_token=medical_record.signature_token,  # Legacy
        signature_hash=medical_record.signature_hash,  # Legacy
        prescription_id=medical_record.prescription_id,
        prescription_token=medical_record.prescription_token,
        patient=medical_record.patient,
    )


@router.put("/{record_id}", response_model=MedicalRecordResponse)
def update_medical_record(
    record_id: int,
    record_data: MedicalRecordUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a medical record (only allowed before signing, during active consultation).
    Only doctors can update medical records they created.
    """
    if current_user.role != Role.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can update medical records"
        )
    
    record = db.query(MedicalRecordModel).filter(MedicalRecordModel.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found"
        )
    
    # Check if doctor created this record
    if record.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update medical records you created"
        )
    
    # Check if record is already signed
    if record.is_signed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update signed medical record"
        )
    
    # Check if consultation is still active
    if not _check_consultation_active(record, db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update medical record after consultation is finished"
        )
    
    # Encrypt updated medical record
    encryption_service = MedicalRecordEncryptionService()
    encrypted_data = encryption_service.encrypt(record_data.medical_record_text)
    
    # Update encrypted fields
    record.encrypted_data = encrypted_data["encryptedData"]
    record.encryption_iv = encrypted_data["iv"]
    record.encryption_auth_tag = encrypted_data["authTag"]
    
    db.commit()
    db.refresh(record)
    
    # Decrypt for response
    decrypted_text = _decrypt_medical_record(record)
    
    return MedicalRecordResponse(
        id=record.id,
        patient_id=record.patient_id,
        doctor_id=record.doctor_id,
        session_id=record.session_id,
        consultation_id=record.consultation_id,
        record_date=record.record_date,
        medical_record_text=decrypted_text,
        is_signed=record.is_signed,
        signed_at=record.signed_at,
        signature_id=record.signature_id,
        signed_hash=record.signed_hash,
        vidaas_certificate_id=record.vidaas_certificate_id,
        vidaas_user_id=record.vidaas_user_id,
        signature_token=record.signature_token,  # Legacy
        signature_hash=record.signature_hash,  # Legacy
        prescription_id=record.prescription_id,
        prescription_token=record.prescription_token,
        patient=record.patient,
    )


@router.post("/{record_id}/sign", response_model=MedicalRecordResponse)
def sign_medical_record(
    record_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sign a medical record using Vidaas ICP.
    After signing, the record cannot be edited and consultation is locked.
    """
    if current_user.role != Role.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can sign medical records"
        )
    
    record = db.query(MedicalRecordModel).filter(MedicalRecordModel.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found"
        )
    
    # Check if doctor created this record
    if record.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only sign medical records you created"
        )
    
    # Check if already signed
    if record.is_signed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medical record is already signed"
        )
    
    # Validate medical record has encrypted data
    if not record.encrypted_data or not record.encryption_iv or not record.encryption_auth_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medical record must be encrypted before signing"
        )
    
    # Get doctor information
    doctor = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if not doctor.crm or not doctor.cpf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor CRM and CPF are required for signing"
        )
    
    # Check doctor has Vidaas credentials
    if not doctor.vidaas_user_id or not doctor.vidaas_certificate_id or not doctor.vidaas_auth_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor must have Vidaas digital certificate registered. Please complete Vidaas registration."
        )
    
    # Decrypt Vidaas auth token (if encrypted)
    from app.services.encryption_service import EncryptionService
    encryption_service = EncryptionService()
    try:
        vidaas_auth_token = encryption_service.decrypt(doctor.vidaas_auth_token)
    except:
        # If decryption fails, assume token is stored in plaintext (for development)
        vidaas_auth_token = doctor.vidaas_auth_token
    
    # Create SHA-256 hash of encrypted record (not decrypted)
    # We sign the encrypted data, not the plaintext
    vidaas_service = VidaasService()
    document_hash = vidaas_service.create_document_hash(record.encrypted_data)
    
    # Prepare metadata
    metadata = {
        "consultationId": str(record.consultation_id) if record.consultation_id else None,
        "sessionId": str(record.session_id) if record.session_id else None,
        "doctorName": doctor.name or "",
        "doctorCRM": doctor.crm,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Sign with Vidaas using doctor's own certificate
    try:
        signature_metadata = vidaas_service.sign_document_hash(
            document_hash=document_hash,
            certificate_id=doctor.vidaas_certificate_id,
            user_id=doctor.vidaas_user_id,
            doctor_auth_token=vidaas_auth_token,
            metadata=metadata
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sign medical record: {str(e)}"
        )
    
    # Update record with signature metadata
    record.is_signed = True
    record.signed_at = datetime.utcnow()
    record.signature_id = signature_metadata.get("signatureId")
    record.signed_hash = signature_metadata.get("signedHash")
    record.vidaas_certificate_id = doctor.vidaas_certificate_id
    record.vidaas_user_id = doctor.vidaas_user_id
    record.signature_metadata = signature_metadata
    
    # Lock consultation/session
    if record.session_id:
        session = db.query(TelemedicineSessionModel).filter(
            TelemedicineSessionModel.id == record.session_id
        ).first()
        if session:
            session.status = "completed"
            session.ended_at = datetime.utcnow()
    
    # Lock appointment/consultation if consultation_id exists
    if record.consultation_id:
        appointment = db.query(AppointmentModel).filter(
            AppointmentModel.id == record.consultation_id
        ).first()
        if appointment:
            appointment.status = "completed"
    
    db.commit()
    db.refresh(record)
    
    # Decrypt record for response (doctor can see it)
    decrypted_text = _decrypt_medical_record(record)
    
    # Return response with decrypted text
    return MedicalRecordResponse(
        id=record.id,
        patient_id=record.patient_id,
        doctor_id=record.doctor_id,
        session_id=record.session_id,
        consultation_id=record.consultation_id,
        record_date=record.record_date,
        medical_record_text=decrypted_text,
        is_signed=record.is_signed,
        signed_at=record.signed_at,
        signature_id=record.signature_id,
        signed_hash=record.signed_hash,
        vidaas_certificate_id=record.vidaas_certificate_id,
        vidaas_user_id=record.vidaas_user_id,
        signature_token=record.signature_token,  # Legacy
        signature_hash=record.signature_hash,  # Legacy
        prescription_id=record.prescription_id,
        prescription_token=record.prescription_token,
        patient=record.patient,
    )


@router.post("/{record_id}/prescription/initiate", response_model=dict)
def initiate_prescription(
    record_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiate prescription creation via Mevo platform.
    Returns Mevo prescription creation URL and reference ID.
    
    Note: Mevo uses webhooks to notify when prescriptions are finalized.
    The webhook will update the medical record automatically.
    """
    if current_user.role != Role.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can create prescriptions"
        )
    
    record = db.query(MedicalRecordModel).filter(MedicalRecordModel.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found"
        )
    
    # Check if doctor created this record
    if record.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create prescriptions for your own medical records"
        )
    
    # Get patient and doctor information
    patient = db.query(UserModel).filter(UserModel.id == record.patient_id).first()
    doctor = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    
    if not patient or not patient.cpf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient CPF is required for prescription"
        )
    
    if not doctor.crm or not doctor.cpf:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor CRM and CPF are required for prescription"
        )
    
    # Generate reference ID for webhook linking
    # Format: "consultation_{id}" or "session_{id}"
    referencia_interna = None
    if record.consultation_id:
        referencia_interna = f"consultation_{record.consultation_id}"
    elif record.session_id:
        referencia_interna = f"session_{record.session_id}"
    else:
        referencia_interna = f"record_{record.id}"
    
    # Get Mevo base URL from environment
    mevo_base_url = os.getenv("MEVO_PRESCRIPTION_URL", "https://prescricao.mevosaude.com.br")
    
    # Return prescription creation URL and reference
    # Note: Actual Mevo URL structure may differ - consult Mevo documentation
    return {
        "prescription_url": f"{mevo_base_url}/prescricao/nova",
        "referencia_interna": referencia_interna,
        "patient_cpf": patient.cpf,
        "patient_name": patient.name,
        "doctor_crm": doctor.crm,
        "doctor_cpf": doctor.cpf,
        "doctor_name": doctor.name,
        "message": "Redirect to Mevo platform to create prescription. Webhook will update medical record when finalized."
    }


@router.get("/{record_id}", response_model=MedicalRecordResponse)
def get_medical_record(
    record_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific medical record by ID.
    Patients CANNOT access medical records (only doctors and admins).
    """
    record = db.query(MedicalRecordModel).filter(MedicalRecordModel.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found"
        )
    
    # Block patient access
    if current_user.role == Role.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients cannot access medical records"
        )
    
    # Check permissions: doctor can only see their own records, admin can see all
    if current_user.role == Role.DOCTOR and record.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own medical records"
        )
    
    # Decrypt for authorized users
    decrypted_text = _decrypt_medical_record(record)
    
    return MedicalRecordResponse(
        id=record.id,
        patient_id=record.patient_id,
        doctor_id=record.doctor_id,
        session_id=record.session_id,
        consultation_id=record.consultation_id,
        record_date=record.record_date,
        medical_record_text=decrypted_text,
        is_signed=record.is_signed,
        signed_at=record.signed_at,
        signature_id=record.signature_id,
        signed_hash=record.signed_hash,
        vidaas_certificate_id=record.vidaas_certificate_id,
        vidaas_user_id=record.vidaas_user_id,
        signature_token=record.signature_token,  # Legacy
        signature_hash=record.signature_hash,  # Legacy
        prescription_id=record.prescription_id,
        prescription_token=record.prescription_token,
        patient=record.patient,
    )


@router.get("/", response_model=List[MedicalRecordResponse])
def get_all_medical_records(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
    patient_id: Optional[int] = Query(None),
    doctor_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get all medical records (admin only).
    Can filter by patient_id or doctor_id.
    """
    # Only admins can see all records
    if current_user.role not in [Role.ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view all medical records"
        )
    
    query = db.query(MedicalRecordModel)
    
    # Apply filters
    if patient_id:
        query = query.filter(MedicalRecordModel.patient_id == patient_id)
    if doctor_id:
        query = query.filter(MedicalRecordModel.doctor_id == doctor_id)
    
    records = query.order_by(MedicalRecordModel.record_date.desc()).offset(skip).limit(limit).all()
    
    # Load patient relationship and decrypt for admin
    result = []
    for record in records:
        _ = record.patient
        decrypted_text = _decrypt_medical_record(record)
        
        result.append(MedicalRecordResponse(
            id=record.id,
            patient_id=record.patient_id,
            doctor_id=record.doctor_id,
            session_id=record.session_id,
            consultation_id=record.consultation_id,
            record_date=record.record_date,
            medical_record_text=decrypted_text,
            is_signed=record.is_signed,
            signed_at=record.signed_at,
            signature_token=record.signature_token,
            signature_hash=record.signature_hash,
            prescription_id=record.prescription_id,
            prescription_token=record.prescription_token,
            patient=record.patient,
        ))
    
    return result


@router.get("/patient/{patient_id}", response_model=List[MedicalRecordResponse])
def get_medical_records_by_patient(
    patient_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all medical records for a specific patient.
    Doctors can see records for patients they treated.
    Admins can see all records.
    Patients CANNOT access medical records.
    """
    # Block patient access
    if current_user.role == Role.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients cannot access medical records"
        )
    
    # Verify patient exists
    patient = db.query(UserModel).filter(UserModel.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    query = db.query(MedicalRecordModel).filter(
        MedicalRecordModel.patient_id == patient_id
    )
    
    # Doctors can only see records they created
    if current_user.role == Role.DOCTOR:
        query = query.filter(MedicalRecordModel.doctor_id == current_user.id)
    
    records = query.order_by(MedicalRecordModel.record_date.desc()).all()
    
    # Decrypt for authorized users
    result = []
    for record in records:
        decrypted_text = _decrypt_medical_record(record)
        
        result.append(MedicalRecordResponse(
            id=record.id,
            patient_id=record.patient_id,
            doctor_id=record.doctor_id,
            session_id=record.session_id,
            consultation_id=record.consultation_id,
            record_date=record.record_date,
            medical_record_text=decrypted_text,
            is_signed=record.is_signed,
            signed_at=record.signed_at,
            signature_token=record.signature_token,
            signature_hash=record.signature_hash,
            prescription_id=record.prescription_id,
            prescription_token=record.prescription_token,
            patient=record.patient,
        ))
    
    return result
