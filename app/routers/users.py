from datetime import datetime  # Import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status, Security
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import FileResponse
from jose import JWTError, jwt  # Import jwt and JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.payment import Payment as PaymentModel  # Import Payment model
from app.models.appointment import Appointment as AppointmentModel
from app.models.medical_record import MedicalRecord as MedicalRecordModel
from app.models.prescription import Prescription as PrescriptionModel
from app.models.telemedicine_session import TelemedicineSession as TelemedicineSessionModel
from app.models.announcement import AnnouncementRead as AnnouncementReadModel, Announcement as AnnouncementModel
from app.models.user import \
    User as UserModel, Role  # Explicitly import and alias User as UserModel
from app.routers.auth import SECRET_KEY  # Import verify_password
from app.routers.auth import ALGORITHM, oauth2_scheme, verify_password

# Create an optional OAuth2 scheme that doesn't raise errors
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
from app.schemas import password as password_schema
from app.schemas import user as user_schema

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Hashes the password after ensuring it does not exceed the 72-character limit for bcrypt.
    """
    # Truncate the string to 72 characters if it's longer
    if len(password) > 72:
        password = password[:72]
    return pwd_context.hash(password)


# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_by_email(db: Session, email: str):
    return db.query(UserModel).filter(UserModel.email == email).first()


# Dependency to get the current user from the JWT token
async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> UserModel:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user


# Optional dependency to get the current user (returns None if not authenticated)
async def get_current_user_optional(
    token: Optional[str] = Security(oauth2_scheme_optional), db: Session = Depends(get_db)
) -> Optional[UserModel]:
    """
    Get the current user if authenticated, otherwise return None.
    Used for endpoints that work with or without authentication.
    """
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        user = get_user_by_email(db, email=email)
        return user
    except (JWTError, Exception):
        return None


@router.get("/", response_model=List[user_schema.User])
def read_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[str] = Query(None, description="Filter by role: customer, doctor, admin, superadmin"),
    db: Session = Depends(get_db)
):
    """
    Get all users with optional role filtering and pagination.
    """
    query = db.query(UserModel)
    
    if role:
        try:
            role_enum = Role(role.lower())
            query = query.filter(UserModel.role == role_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}. Must be one of: customer, doctor, admin, superadmin")
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/me", response_model=user_schema.UserMeResponse)
def read_users_me(
    current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get the current logged-in user's information, including active payment status and phone number.
    """
    active_payment = (
        db.query(PaymentModel)
        .filter(
            PaymentModel.user_id == current_user.id,
            PaymentModel.end_date > datetime.utcnow(),
        )
        .first()
    )
    has_active_payment = active_payment is not None

    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "is_active": current_user.is_active,
        "phone": current_user.phone,
        "cpf": current_user.cpf,
        "has_active_payment": has_active_payment,
        "role": current_user.role,
        # Doctor-specific fields
        "crm": current_user.crm,
        "uf_crm": current_user.uf_crm,
        "primary_specialty": current_user.primary_specialty,
        "bank_information": current_user.bank_information,
        "attached_document": current_user.attached_document,
        "career_resume": current_user.career_resume,
        "photo": current_user.photo,
        # Google OAuth fields - use getattr with default False for safety
        "profile_completed": getattr(current_user, 'profile_completed', None) if hasattr(current_user, 'profile_completed') else False,
        "google_calendar_enabled": getattr(current_user, 'google_calendar_enabled', None) if hasattr(current_user, 'google_calendar_enabled') else False,
    }


@router.put("/me", response_model=user_schema.UserMeResponse)
def update_current_user(
    user_update: user_schema.UserUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the current logged-in user's information.
    """
    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    # Don't allow updating email or role via this endpoint
    update_data.pop('email', None)
    update_data.pop('role', None)
    
    for key, value in update_data.items():
        setattr(current_user, key, value)
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    
    # Return updated user with same format as GET /users/me
    active_payment = (
        db.query(PaymentModel)
        .filter(
            PaymentModel.user_id == current_user.id,
            PaymentModel.end_date > datetime.utcnow(),
        )
        .first()
    )
    has_active_payment = active_payment is not None
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "is_active": current_user.is_active,
        "phone": current_user.phone,
        "cpf": current_user.cpf,
        "has_active_payment": has_active_payment,
        "role": current_user.role,
        "crm": current_user.crm,
        "uf_crm": current_user.uf_crm,
        "primary_specialty": current_user.primary_specialty,
        "bank_information": current_user.bank_information,
        "attached_document": current_user.attached_document,
        "career_resume": current_user.career_resume,
        "photo": current_user.photo,
        # Google OAuth fields - use getattr with default False for safety
        "profile_completed": getattr(current_user, 'profile_completed', None) if hasattr(current_user, 'profile_completed') else False,
        "google_calendar_enabled": getattr(current_user, 'google_calendar_enabled', None) if hasattr(current_user, 'google_calendar_enabled') else False,
    }


@router.post("/me/photo", status_code=status.HTTP_200_OK)
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a profile photo for the current user.
    """
    import uuid
    from pathlib import Path
    
    # Create uploads directory if it doesn't exist
    UPLOAD_DIR = Path("uploads/photos")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Allowed image types
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Read file content to check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024 * 1024)}MB"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_name = f"{file_id}{file_ext}"
    file_path = UPLOAD_DIR / file_name
    
    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Get user from current session
    db_user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Delete old photo if exists
    if db_user.photo:
        old_photo_path = Path(db_user.photo.replace("/photos/", "uploads/photos/"))
        if old_photo_path.exists():
            try:
                old_photo_path.unlink()
            except Exception:
                pass  # Ignore errors when deleting old photo
    
    # Update user's photo field
    photo_url = f"/users/photos/{file_name}"
    db_user.photo = photo_url
    db.commit()
    db.refresh(db_user)
    
    return {"photo_url": photo_url}


@router.get("/photos/{file_name}")
async def get_profile_photo(
    file_name: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Get a profile photo file. Authentication is optional - photos can be viewed by anyone
    who has the URL (UUID-based filename provides security through obscurity).
    """
    from pathlib import Path
    
    file_path = Path("uploads/photos") / file_name
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # If user is authenticated, verify they own the photo (optional check)
    # But allow viewing even if not authenticated (for image previews in browsers)
    if current_user and current_user.photo and file_name in current_user.photo:
        # User owns this photo, allow access
        pass
    # If not authenticated or doesn't own it, still allow access
    # (UUID filename provides security through obscurity)
    
    # Determine media type based on file extension
    media_type = "image/jpeg" if file_name.lower().endswith(('.jpg', '.jpeg')) else "image/png"
    
    return FileResponse(
        path=str(file_path),
        media_type=media_type
    )


@router.get("/{user_id}", response_model=user_schema.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    """
    Get a user by ID.
    """
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=user_schema.User)
def update_user(
    user_id: int,
    user_update: user_schema.UserBase,
    db: Session = Depends(get_db)
):
    """
    Update a user by ID.
    """
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently delete a user from the database.
    Only admins and superadmins can delete users.
    This will also delete related records (appointments, medical records, etc.)
    if foreign key constraints allow cascade deletion.
    """
    # Check if current user is admin or superadmin
    if current_user.role not in [Role.ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete users"
        )
    
    db_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting admins/superadmins (only allow deleting customers and doctors)
    if db_user.role in [Role.ADMIN, Role.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete admin or superadmin users"
        )
    
    # Prevent self-deletion
    if db_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    try:
        user_id = db_user.id
        
        # Delete all related records before deleting the user
        # 1. Delete appointments where user is patient or doctor
        db.query(AppointmentModel).filter(
            (AppointmentModel.patient_id == user_id) | 
            (AppointmentModel.doctor_id == user_id)
        ).delete()
        
        # 2. Delete medical records where user is patient or doctor
        db.query(MedicalRecordModel).filter(
            (MedicalRecordModel.patient_id == user_id) | 
            (MedicalRecordModel.doctor_id == user_id)
        ).delete()
        
        # 3. Delete prescriptions where user is patient or prescriber
        db.query(PrescriptionModel).filter(
            (PrescriptionModel.patient_id == user_id) | 
            (PrescriptionModel.prescriber_id == user_id)
        ).delete()
        
        # 4. Delete telemedicine sessions where user is patient or doctor
        db.query(TelemedicineSessionModel).filter(
            (TelemedicineSessionModel.patient_id == user_id) | 
            (TelemedicineSessionModel.doctor_id == user_id)
        ).delete()
        
        # 5. Delete payments for the user
        db.query(PaymentModel).filter(PaymentModel.user_id == user_id).delete()
        
        # 6. Delete announcement reads for the user
        db.query(AnnouncementReadModel).filter(AnnouncementReadModel.user_id == user_id).delete()
        
        # 7. Handle announcements created by the user (set created_by_id to NULL or delete)
        # Option: Set created_by_id to NULL to preserve announcements
        # Or delete announcements created by this user
        # For now, we'll delete announcements created by this user
        db.query(AnnouncementModel).filter(AnnouncementModel.created_by_id == user_id).delete()
        
        # 8. Handle announcements where user is recipient (set recipient_id to NULL)
        # Since recipient_id is nullable, we can set it to NULL
        db.query(AnnouncementModel).filter(AnnouncementModel.recipient_id == user_id).update({AnnouncementModel.recipient_id: None})
        
        # Now delete the user
        db.delete(db_user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )
    return


@router.post("/", response_model=user_schema.User)
def create_user(user: user_schema.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        email=user.email,
        hashed_password=hashed_password,
        name=user.name,
        gender=user.gender,
        cpf=user.cpf,
        phone=user.phone,
        birthday=user.birthday,
        cep=user.cep,
        logradouro=user.logradouro,
        numero=user.numero,
        complemento=user.complemento,
        bairro=user.bairro,
        estado=user.estado,
        cidade=user.cidade,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def update_password(
    password_update: password_schema.PasswordUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(
        password_update.current_password, current_user.hashed_password
    ):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    if password_update.new_password != password_update.confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")

    current_user.hashed_password = get_password_hash(password_update.new_password)
    db.add(current_user)
    db.commit()
