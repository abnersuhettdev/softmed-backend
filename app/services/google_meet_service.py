import os
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from google.auth.transport.requests import \
    Request as GoogleAuthRequest  # Needed for token refresh
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.models.user import User as UserModel
from app.services.google_oauth_service import GoogleOAuthService

load_dotenv()


class GoogleMeetService:
    def __init__(self, doctor_id: int, db: Session):
        """
        Initialize GoogleMeetService with doctor's Google credentials.
        
        Args:
            doctor_id: ID of the doctor whose Google credentials to use
            db: Database session
        """
        # Load doctor from database
        doctor = db.query(UserModel).filter(UserModel.id == doctor_id).first()
        
        if not doctor:
            raise Exception(f"Doctor with ID {doctor_id} not found")
        
        if not doctor.google_access_token or not doctor.google_refresh_token:
            raise Exception(f"Doctor {doctor_id} has not connected Google Calendar")
        
        if not doctor.google_calendar_enabled:
            raise Exception(f"Doctor {doctor_id} has not enabled Google Calendar")
        
        # Initialize OAuth service for token decryption and refresh
        oauth_service = GoogleOAuthService()
        
        # Decrypt tokens
        access_token = oauth_service.decrypt_token(doctor.google_access_token)
        refresh_token = oauth_service.decrypt_token(doctor.google_refresh_token)
        
        # Get client credentials from environment
        google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        if not google_client_id or not google_client_secret:
            raise Exception("Missing Google API credentials in environment variables.")

        # --- Corrected Scope ---
        # The broader Calendar scope is more reliable for Meet creation
        SCOPES = ["https://www.googleapis.com/auth/calendar"]

        # --- Initialize Credentials ---
        # Check if token is expired
        token_expired = False
        if doctor.google_token_expires_at:
            token_expired = datetime.utcnow() >= doctor.google_token_expires_at
        
        self.creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=google_client_id,
            client_secret=google_client_secret,
            scopes=SCOPES,
        )
        
        # Set expiry if we have the expiry time
        if doctor.google_token_expires_at:
            self.creds.expiry = doctor.google_token_expires_at

        # --- Refresh Token if Expired ---
        # Refresh token if expired or about to expire (within 5 minutes)
        if token_expired or (self.creds.expiry and (self.creds.expiry - datetime.utcnow()).total_seconds() < 300):
            try:
                self.creds.refresh(GoogleAuthRequest())
                
                # Update doctor's tokens in database
                new_access_token = self.creds.token
                new_expires_in = 3600  # Default 1 hour
                if self.creds.expiry:
                    new_expires_in = int((self.creds.expiry - datetime.utcnow()).total_seconds())
                
                # Encrypt and store new tokens
                doctor.google_access_token = oauth_service.encrypt_token(new_access_token)
                doctor.google_token_expires_at = oauth_service.calculate_token_expiry(new_expires_in)
                db.commit()
            except Exception as e:
                raise Exception(f"Failed to refresh Google token: {str(e)}")

        # Build the Google Calendar service object
        self.service = build("calendar", "v3", credentials=self.creds)

    def create_meeting(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str],
    ):
        # This function attempts to refresh the token again just before the call,
        # providing an extra layer of protection against expiration.
        if self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(GoogleAuthRequest())

        # For personal Google accounts: Don't add attendees to the calendar event
        # This prevents approval prompts. The Meet link will work for anyone.
        # We'll send the link separately to doctor and patient.
        event = {
            "summary": summary,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "America/Sao_Paulo",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "America/Sao_Paulo",
            },
            # Don't add attendees to avoid approval prompts for personal accounts
            # The Meet link will work for anyone with the link
            "conferenceData": {
                # This key is required to instruct Google to create a Meet conference
                "createRequest": {
                    "requestId": "fastapi-meet-request-"
                    + str(int(datetime.now().timestamp())),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
            # Allow anyone with the link to join without approval
            "anyoneCanAddSelf": True,  # Allow anyone with the link to join
            # Set visibility to public so the link works for anyone
            "visibility": "public",
            # For personal accounts: Make the event immediately accessible
            "transparency": "opaque",  # Don't mark as "free" time
        }

        try:
            # conferenceDataVersion=1 is MANDATORY for 'conferenceData' to be processed
            event = (
                self.service.events()
                .insert(
                    calendarId="primary",
                    body=event,
                    conferenceDataVersion=1,
                    sendNotifications=True,
                )
                .execute()
            )

            # The meeting link is returned in the 'hangoutLink' field
            return event.get("hangoutLink")

        except Exception as e:
            # This is the proper place to raise an exception for the calling function
            raise Exception(f"Failed to create Google Meet event: {e}")


# Example usage (assuming you define your datetime objects and run this in a main block)
# from datetime import timedelta
# meet_service = GoogleMeetService()
# now = datetime.now()
# link = meet_service.create_meeting("Test FastAPI Meeting", now, now + timedelta(hours=1), ["user@example.com"])
# print(link)
