from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    session_id = Column(Integer, nullable=True)  # Link to telemedicine session
    consultation_id = Column(Integer, nullable=True)  # Link to consultation/appointment
    record_date = Column(DateTime, default=datetime.utcnow)
    
    # New encrypted medical record (single text field)
    encrypted_data = Column(Text, nullable=True)  # AES-256-GCM encrypted medical record
    encryption_iv = Column(String, nullable=True)  # Initialization vector (base64)
    encryption_auth_tag = Column(String, nullable=True)  # Authentication tag (base64)
    
    # Digital signature metadata (Vidaas)
    is_signed = Column(Boolean, default=False, nullable=False)
    signed_at = Column(DateTime, nullable=True)
    signature_id = Column(String, nullable=True)  # Vidaas signature ID
    signed_hash = Column(String, nullable=True)  # SHA-256 hash of encrypted record (signed)
    vidaas_certificate_id = Column(String, nullable=True)  # Vidaas certificate ID used for signing
    vidaas_user_id = Column(String, nullable=True)  # Vidaas user ID who signed
    signature_metadata = Column(JSON, nullable=True)  # Full signature metadata from Vidaas
    # Legacy fields (deprecated)
    signature_token = Column(String, nullable=True)  # Deprecated - use signature_id
    signature_hash = Column(String, nullable=True)  # Deprecated - use signed_hash
    vidaas_document_id = Column(String, nullable=True)  # Deprecated
    
    # Electronic prescription metadata (Mevo)
    prescription_id = Column(String, nullable=True)  # Mevo prescription ID
    prescription_token = Column(String, nullable=True)  # Mevo prescription token
    prescription_metadata = Column(JSON, nullable=True)  # Full prescription metadata from Mevo
    
    # Legacy fields (deprecated, kept for migration compatibility)
    complaints = Column(Text, nullable=True)  # Deprecated - use encrypted_data
    symptoms = Column(Text, nullable=True)  # Deprecated - use encrypted_data
    conduct = Column(Text, nullable=True)  # Deprecated - use encrypted_data
    orientation = Column(Text, nullable=True)  # Deprecated - use encrypted_data
    diagnosis = Column(Text, nullable=True)  # Deprecated - use encrypted_data
    treatment = Column(Text, nullable=True)  # Deprecated - use encrypted_data

    patient = relationship("User", foreign_keys=[patient_id], back_populates="medical_records")
