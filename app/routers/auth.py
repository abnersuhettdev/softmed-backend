import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User as UserModel, Role
from app.schemas.user import (ForgotPasswordRequest, ResetPasswordRequest,
                              UserLogin)
from app.services.email_service import send_reset_email
from app.services.google_oauth_service import GoogleOAuthService
from fastapi.responses import RedirectResponse

load_dotenv()

router = APIRouter()


@router.get("/google/test")
async def test_google_oauth():
    """Test endpoint to verify Google OAuth configuration."""
    try:
        oauth_service = GoogleOAuthService()
        return {
            "status": "ok",
            "client_id_set": bool(oauth_service.client_id),
            "client_secret_set": bool(oauth_service.client_secret),
            "redirect_uri": oauth_service.redirect_uri,
            "frontend_url": oauth_service.frontend_url,
            "instructions": {
                "step1": "Copy the redirect_uri above",
                "step2": "Go to https://console.cloud.google.com/apis/credentials",
                "step3": "Open your OAuth 2.0 Client ID",
                "step4": f"Add '{oauth_service.redirect_uri}' to 'Authorized redirect URIs'",
                "step5": "Save and wait a few minutes for changes to propagate"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
BASE_URL = os.getenv(
    "FRONTEND_DOCTOR_BASE_URL", "http://localhost:5173"
)  # Default for development

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@router.get("/google/login")
async def google_login(request: Request, frontend_url: Optional[str] = None):
    """
    Initiate Google OAuth flow.
    Generates state token and redirects to Google OAuth page.
    
    Args:
        frontend_url: Optional frontend URL to redirect back to (can be passed as query param)
    """
    try:
        oauth_service = GoogleOAuthService()
        
        # Get frontend URL from query param, referer, or env var
        if not frontend_url:
            referer = request.headers.get("referer")
            if referer:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(referer)
                    frontend_url = f"{parsed.scheme}://{parsed.netloc}"
                except:
                    frontend_url = oauth_service.frontend_url
            else:
                frontend_url = oauth_service.frontend_url
        
        state = oauth_service.generate_state_token()
        oauth_service.store_state_token(state, frontend_url=frontend_url)
        
        auth_url = oauth_service.generate_authorization_url(state)
        print(f"Redirecting to Google OAuth with frontend_url={frontend_url}: {auth_url[:100]}...")
        return RedirectResponse(url=auth_url, status_code=302)
    except ValueError as e:
        # Missing environment variables
        print(f"Google OAuth configuration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        )
    except Exception as e:
        print(f"Google OAuth error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Google OAuth: {str(e)}"
        )


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback.
    Exchanges code for tokens, creates/logs in doctor, and redirects to frontend with JWT token.
    """
    oauth_service = GoogleOAuthService()
    
    # Try to get frontend URL from referer header or origin, fallback to env var
    frontend_url = oauth_service.frontend_url
    referer = request.headers.get("referer")
    origin = request.headers.get("origin")
    
    if referer:
        # Extract origin from referer (e.g., "http://localhost:5174" from "http://localhost:5174/login")
        try:
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            frontend_url = f"{parsed.scheme}://{parsed.netloc}"
            print(f"Using frontend URL from referer: {frontend_url}")
        except Exception as e:
            print(f"Failed to parse referer: {e}")
    elif origin:
        frontend_url = origin
        print(f"Using frontend URL from origin: {frontend_url}")
    else:
        print(f"Using frontend URL from env/default: {frontend_url}")
    
    # Handle OAuth errors
    if error:
        error_url = f"{frontend_url}/auth/google/callback#error={error}"
        return RedirectResponse(url=error_url)
    
    # Validate required parameters
    if not code or not state:
        error_url = f"{frontend_url}/auth/google/callback#error=missing_parameters"
        return RedirectResponse(url=error_url)
    
    # Verify state token (CSRF protection)
    state_valid, stored_frontend_url = oauth_service.verify_state_token(state)
    if not state_valid:
        error_url = f"{frontend_url}/auth/google/callback#error=invalid_state"
        return RedirectResponse(url=error_url)
    
    # Use frontend URL from state token if available (most reliable)
    if stored_frontend_url:
        frontend_url = stored_frontend_url
        print(f"Using frontend URL from state token: {frontend_url}")
    
    try:
        # Exchange code for tokens
        token_data = oauth_service.exchange_code_for_tokens(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        
        if not access_token or not refresh_token:
            raise Exception("Failed to get tokens from Google")
        
        # Get user info from Google
        user_info = oauth_service.get_google_user_info(access_token)
        google_email = user_info.get("email")
        google_name = user_info.get("name", "")
        
        if not google_email:
            raise Exception("Failed to get email from Google")
        
        # Check if user exists (any role)
        existing_user = db.query(UserModel).filter(
            UserModel.email == google_email
        ).first()
        
        # Encrypt tokens before storing
        encrypted_access_token = oauth_service.encrypt_token(access_token)
        encrypted_refresh_token = oauth_service.encrypt_token(refresh_token)
        
        # Calculate token expiry
        token_expires_at = oauth_service.calculate_token_expiry(expires_in)
        
        if existing_user:
            # User exists - check if they're a doctor
            if existing_user.role != Role.DOCTOR:
                # User exists but is not a doctor - check if they're admin or customer
                if existing_user.role in [Role.ADMIN, Role.CUSTOMER, Role.SUPERADMIN]:
                    # Block login - user is already admin or customer
                    error_message = "You are already a member of this system as an admin or customer. Doctor access is not allowed."
                    print(f"Blocking Google OAuth login for {google_email} - existing role: {existing_user.role}")
                    error_url = f"{frontend_url}/auth/google/callback#error=role_conflict&message={quote(error_message)}"
                    return RedirectResponse(url=error_url)
                else:
                    # Unknown role - also block for safety
                    error_message = "You are already a member of this system as an admin or customer. Doctor access is not allowed."
                    print(f"Blocking Google OAuth login for {google_email} - unknown role: {existing_user.role}")
                    error_url = f"{frontend_url}/auth/google/callback#error=role_conflict&message={quote(error_message)}"
                    return RedirectResponse(url=error_url)
            
            # Existing doctor - update tokens and log in
            doctor = existing_user
            doctor.google_access_token = encrypted_access_token
            doctor.google_refresh_token = encrypted_refresh_token
            doctor.google_calendar_enabled = True  # Calendar scope is included
            doctor.google_token_expires_at = token_expires_at
            # Update name if provided and not set
            if google_name and not doctor.name:
                doctor.name = google_name
        else:
            # New doctor - create account
            # Double-check if user exists (race condition protection)
            check_user = db.query(UserModel).filter(UserModel.email == google_email).first()
            if check_user:
                # User was created between our check and now, or exists with different role
                if check_user.role != Role.DOCTOR:
                    # Check if they're admin or customer - block login
                    if check_user.role in [Role.ADMIN, Role.CUSTOMER, Role.SUPERADMIN]:
                        # Block login - user is already admin or customer
                        error_message = "You are already a member of this system as an admin or customer. Doctor access is not allowed."
                        print(f"Blocking Google OAuth login for {google_email} - existing role: {check_user.role}")
                        error_url = f"{frontend_url}/auth/google/callback#error=role_conflict&message={quote(error_message)}"
                        return RedirectResponse(url=error_url)
                    else:
                        # Unknown role - also block for safety
                        error_message = "You are already a member of this system as an admin or customer. Doctor access is not allowed."
                        print(f"Blocking Google OAuth login for {google_email} - unknown role: {check_user.role}")
                        error_url = f"{frontend_url}/auth/google/callback#error=role_conflict&message={quote(error_message)}"
                        return RedirectResponse(url=error_url)
                # User is a doctor, use existing
                doctor = check_user
                doctor.google_access_token = encrypted_access_token
                doctor.google_refresh_token = encrypted_refresh_token
                doctor.google_calendar_enabled = True
                doctor.google_token_expires_at = token_expires_at
                if google_name and not doctor.name:
                    doctor.name = google_name
            else:
                # Truly new doctor - create account
                doctor = UserModel(
                    email=google_email,
                    name=google_name,
                    role=Role.DOCTOR,
                    google_access_token=encrypted_access_token,
                    google_refresh_token=encrypted_refresh_token,
                    google_calendar_enabled=True,  # Calendar scope is included
                    google_token_expires_at=token_expires_at,
                    profile_completed=False,  # Must complete profile
                    is_active=True,
                )
                db.add(doctor)
        
        try:
            db.commit()
            db.refresh(doctor)
        except Exception as db_error:
            db.rollback()
            # Check if it's a unique constraint violation
            error_str = str(db_error)
            if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                # User was created between checks - fetch and update
                existing_doctor = db.query(UserModel).filter(
                    UserModel.email == google_email,
                    UserModel.role == Role.DOCTOR
                ).first()
                if existing_doctor:
                    existing_doctor.google_access_token = encrypted_access_token
                    existing_doctor.google_refresh_token = encrypted_refresh_token
                    existing_doctor.google_calendar_enabled = True
                    existing_doctor.google_token_expires_at = token_expires_at
                    if google_name and not existing_doctor.name:
                        existing_doctor.name = google_name
                    db.commit()
                    db.refresh(existing_doctor)
                    doctor = existing_doctor
                else:
                    # User exists but not as doctor - check if they're admin or customer
                    existing_user = db.query(UserModel).filter(UserModel.email == google_email).first()
                    if existing_user:
                        # Check if they're admin or customer - block login
                        if existing_user.role in [Role.ADMIN, Role.CUSTOMER, Role.SUPERADMIN]:
                            # Block login - user is already admin or customer
                            error_message = "You are already a member of this system as an admin or customer. Doctor access is not allowed."
                            print(f"Blocking Google OAuth login for {google_email} - existing role: {existing_user.role}")
                            error_url = f"{frontend_url}/auth/google/callback#error=role_conflict&message={quote(error_message)}"
                            return RedirectResponse(url=error_url)
                        else:
                            # Unknown role - also block for safety
                            error_message = "You are already a member of this system as an admin or customer. Doctor access is not allowed."
                            print(f"Blocking Google OAuth login for {google_email} - unknown role: {existing_user.role}")
                            error_url = f"{frontend_url}/auth/google/callback#error=role_conflict&message={quote(error_message)}"
                            return RedirectResponse(url=error_url)
                    else:
                        # Should not happen, but handle it
                        raise Exception("Database error: User exists but cannot be found")
            else:
                # Other database error
                raise db_error
        
        # Generate JWT token for our application
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        jwt_token = create_access_token(
            data={"sub": doctor.email}, expires_delta=access_token_expires
        )
        
        # Redirect to frontend with token and profile completion status
        profile_completed = doctor.profile_completed or False
        redirect_url = f"{frontend_url}/auth/google/callback#token={jwt_token}&profile_completed={str(profile_completed).lower()}"
        
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        # Log error for debugging
        print(f"Google OAuth callback error: {str(e)}")
        error_url = f"{frontend_url}/auth/google/callback#error=oauth_failed"
        return RedirectResponse(url=error_url)


@router.post("/token", response_model=dict)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    user = db.query(UserModel).filter(UserModel.email == request.email).first()
    if not user:
        # For security, don't reveal if the user doesn't exist
        return {
            "message": "If a user with that email exists, a password reset link will be sent."
        }

    token = secrets.token_urlsafe(32)
    hashed_token = pwd_context.hash(token)
    expires_at = datetime.utcnow() + timedelta(hours=1)  # Token valid for 1 hour

    user.password_reset_token = hashed_token
    user.password_reset_expires_at = expires_at
    db.add(user)
    db.commit()
    db.refresh(user)

    reset_link = f"{BASE_URL}/reset-password?token={token}"
    send_reset_email(user.email, reset_link)

    return {
        "message": "If a user with that email exists, a password reset link will be sent."
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match"
        )

    user = (
        db.query(UserModel)
        .filter(
            UserModel.password_reset_token != None,
            UserModel.password_reset_expires_at > datetime.utcnow(),
        )
        .first()
    )

    if not user or not pwd_context.verify(request.token, user.password_reset_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token"
        )

    # Hash the new password and update in DB
    user.hashed_password = pwd_context.hash(request.new_password)
    user.password_reset_token = None  # Invalidate token
    user.password_reset_expires_at = None  # Clear expiry
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "Password has been reset successfully."}
