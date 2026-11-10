from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel


class PatientInfo(BaseModel):
    """Simplified patient info to avoid recursion"""
    id: int
    email: str
    name: Optional[str] = None

    class Config:
        from_attributes = True


class MedicalRecordCreate(BaseModel):
    """Create a new medical record (single text field)"""
    patient_id: int
    session_id: int | None = None
    consultation_id: int | None = None
    medical_record_text: str  # Single text field containing all medical information


class MedicalRecordUpdate(BaseModel):
    """Update medical record (only allowed before signing)"""
    medical_record_text: str


class MedicalRecordSignRequest(BaseModel):
    """Request to sign a medical record with Vidaas"""
    record_id: int


class MedicationItem(BaseModel):
    """Medication item for prescription"""
    name: str
    dosage: str
    quantity: str
    instructions: str | None = None


class MedicalRecordPrescriptionRequest(BaseModel):
    """Request to create electronic prescription via Mevo"""
    record_id: int
    medications: List[MedicationItem]


class MedicalRecordResponse(BaseModel):
    """Medical record response (decrypted for authorized users)"""
    id: int
    patient_id: int
    doctor_id: int | None = None
    session_id: int | None = None
    consultation_id: int | None = None
    record_date: datetime
    
    # Decrypted medical record (only for authorized users)
    medical_record_text: str | None = None
    
    # Signature status
    is_signed: bool
    signed_at: datetime | None = None
    signature_id: str | None = None  # Vidaas signature ID
    signed_hash: str | None = None  # SHA-256 hash of encrypted record (signed)
    vidaas_certificate_id: str | None = None  # Vidaas certificate ID used
    vidaas_user_id: str | None = None  # Vidaas user ID who signed
    # Legacy fields (deprecated)
    signature_token: str | None = None  # Deprecated - use signature_id
    signature_hash: str | None = None  # Deprecated - use signed_hash
    
    # Prescription status
    prescription_id: str | None = None
    prescription_token: str | None = None
    
    # Patient info
    patient: Optional[PatientInfo] = None

    class Config:
        from_attributes = True


# Legacy schemas for backward compatibility (deprecated)
class MedicalRecordBase(BaseModel):
    record_date: datetime = datetime.utcnow()
    complaints: str | None = None
    symptoms: str | None = None
    conduct: str | None = None
    orientation: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None


class MedicalRecord(MedicalRecordBase):
    """Legacy schema - deprecated, use MedicalRecordResponse instead"""
    id: int
    patient_id: int
    doctor_id: int | None = None
    session_id: int | None = None
    patient: Optional[PatientInfo] = None

    class Config:
        from_attributes = True
