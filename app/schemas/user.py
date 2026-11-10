from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.user import Role


class UserBase(BaseModel):
    email: str
    name: Optional[str] = None
    gender: Optional[str] = None
    cpf: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[date] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    estado: Optional[str] = None
    cidade: Optional[str] = None
    role: Optional[Role] = None

    # Doctor-specific fields
    crm: Optional[str] = None
    uf_crm: Optional[str] = None
    primary_specialty: Optional[str] = None
    bank_information: Optional[str] = None
    attached_document: Optional[str] = None
    photo: Optional[str] = None
    telemedicine_access: Optional[bool] = None
    queue_open: Optional[bool] = None


class UserCreate(UserBase):
    password: str = Field(..., max_length=72)


class UserUpdate(BaseModel):
    """Schema for updating user information - all fields are optional"""
    email: Optional[str] = None
    name: Optional[str] = None
    gender: Optional[str] = None
    cpf: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[date] = None
    cep: Optional[str] = None
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    estado: Optional[str] = None
    cidade: Optional[str] = None
    role: Optional[Role] = None
    
    # Doctor-specific fields
    crm: Optional[str] = None
    uf_crm: Optional[str] = None
    primary_specialty: Optional[str] = None
    bank_information: Optional[str] = None
    attached_document: Optional[str] = None
    career_resume: Optional[str] = None
    photo: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., max_length=72)
    confirm_password: str = Field(..., max_length=72)


class User(UserBase):
    id: int
    is_active: bool
    role: Role
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    estado: Optional[str] = None
    cidade: Optional[str] = None
    profile_completed: Optional[bool] = False
    google_calendar_enabled: Optional[bool] = False
    medical_records: List["MedicalRecord"] = []
    prescriptions: List["Prescription"] = []

    class Config:
        from_attributes = True


class UserBaseInfo(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    is_active: bool
    role: Role


class UserMeResponse(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    is_active: bool
    phone: Optional[str] = None
    cpf: Optional[str] = None
    has_active_payment: bool
    role: Role

    # Doctor-specific fields
    crm: Optional[str] = None
    uf_crm: Optional[str] = None
    primary_specialty: Optional[str] = None
    bank_information: Optional[str] = None
    attached_document: Optional[str] = None
    career_resume: Optional[str] = None
    profile_completed: Optional[bool] = False
    google_calendar_enabled: Optional[bool] = False
    photo: Optional[str] = None


class DoctorProfileCompletion(BaseModel):
    """Schema for doctor profile completion after Google OAuth signup."""
    name: Optional[str] = None  # Optional - can update if needed (already set from Google)
    cpf: Optional[str] = None
    phone: Optional[str] = None
    crm: Optional[str] = None
    uf_crm: Optional[str] = None
    primary_specialty: Optional[str] = None


# Import after User is defined to avoid circular import
from app.schemas.medical_record import MedicalRecord
from app.schemas.prescription import Prescription

User.update_forward_refs()
