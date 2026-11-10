import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Enum as EnumDB
from sqlalchemy.orm import relationship

from app.database import Base


class Role(str, enum.Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    CUSTOMER = "customer"
    DOCTOR = "doctor"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(EnumDB(Role), default=Role.CUSTOMER, nullable=False)

    # New fields
    name = Column(String, index=True)
    gender = Column(String)
    cpf = Column(String, unique=True, index=True)
    phone = Column(String)
    birthday = Column(Date)
    cep = Column(String)
    logradouro = Column(String)
    numero = Column(String)
    complemento = Column(String, nullable=True)
    bairro = Column(String)
    estado = Column(String)
    cidade = Column(String)

    # Doctor-specific fields
    crm = Column(String, nullable=True)
    uf_crm = Column(String, nullable=True)
    primary_specialty = Column(String, nullable=True, index=True)  # e.g., "Cardiology", "Dermatology", "Pediatrics"
    bank_information = Column(String, nullable=True)
    attached_document = Column(String, nullable=True)
    career_resume = Column(String, nullable=True)  # Career resume/history text
    photo = Column(String, nullable=True)  # Profile photo URL/path
    telemedicine_access = Column(Boolean, default=False, nullable=True)  # Doctor telemedicine access
    queue_open = Column(Boolean, default=False, nullable=True)  # Doctor queue open/closed status

    # Password reset fields
    password_reset_token = Column(String, nullable=True)
    password_reset_expires_at = Column(DateTime, nullable=True)

    # Google OAuth fields (for doctors)
    google_access_token = Column(String, nullable=True)  # Encrypted
    google_refresh_token = Column(String, nullable=True)  # Encrypted
    google_calendar_enabled = Column(Boolean, default=False, nullable=True)
    profile_completed = Column(Boolean, default=False, nullable=True)
    google_token_expires_at = Column(DateTime, nullable=True)
    
    # Vidaas digital certificate fields (for doctors)
    vidaas_user_id = Column(String, nullable=True)  # Vidaas user ID
    vidaas_certificate_id = Column(String, nullable=True)  # Vidaas certificate ID
    vidaas_auth_token = Column(String, nullable=True)  # Doctor's Vidaas auth token (encrypted)

    medical_records = relationship("MedicalRecord", foreign_keys="MedicalRecord.patient_id", back_populates="patient")
    prescriptions = relationship(
        "Prescription",
        foreign_keys="[Prescription.patient_id]",
        back_populates="patient",
    )
    appointments_as_patient = relationship(
        "Appointment", foreign_keys="[Appointment.patient_id]", back_populates="patient"
    )
    appointments_as_doctor = relationship(
        "Appointment", foreign_keys="[Appointment.doctor_id]", back_populates="doctor"
    )
    prescriptions_as_prescriber = relationship(
        "Prescription",
        foreign_keys="[Prescription.prescriber_id]",
        back_populates="prescriber",
    )
    payments = relationship("Payment", back_populates="user")

    # Queue management fields
    queue_status = Column(
        String, index=True, default="waiting"
    )  # e.g., 'waiting', 'in_service', 'completed', 'no_wait'
    queue_entry_time = Column(DateTime, nullable=True)

    # Telemedicine session relationships
    telemedicine_sessions_as_patient = relationship(
        "TelemedicineSession", foreign_keys="[TelemedicineSession.patient_id]", back_populates="patient"
    )
    telemedicine_sessions_as_doctor = relationship(
        "TelemedicineSession", foreign_keys="[TelemedicineSession.doctor_id]", back_populates="doctor"
    )
