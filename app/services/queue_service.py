import os
from datetime import datetime, timedelta
from typing import List, Optional

from dotenv import load_dotenv
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.database import SessionLocal
from app.models.telemedicine_session import TelemedicineSession
from app.models.user import User
from app.services.google_meet_service import GoogleMeetService
from app.services.settings_service import SettingsService
from app.services.telemedicine_session_service import TelemedicineSessionService

load_dotenv()

# Try to import redis, but make it optional
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class QueueService:
    def __init__(self):
        self.redis = None
        self.redis_enabled = False
        self.queue_name = "patient_queue"
        
        # Try to connect to Redis if available, but don't fail if it's not
        if REDIS_AVAILABLE:
            try:
                self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self.redis = redis.from_url(self.redis_url, socket_connect_timeout=1)
                # Test connection
                self.redis.ping()
                self.redis_enabled = True
                print("Redis connected successfully. Queue will use Redis for fast operations.")
            except Exception as e:
                print(f"Redis not available: {e}. Queue will use database-only mode.")
                self.redis_enabled = False
                self.redis = None
        else:
            print("Redis library not installed. Queue will use database-only mode.")

    @staticmethod
    def get_db_session() -> Session:
        """Get a database session. Caller is responsible for closing it."""
        return SessionLocal()

    def is_queue_available(self) -> bool:
        """Check if queue is available for patients to join."""
        db = self.get_db_session()
        try:
            settings_service = SettingsService(db)
            # 1. Check admin setting
            if not settings_service.is_telemedicine_enabled():
                return False
            # 2. Check if any doctor has queue open
            doctors_with_open_queue = self.get_doctors_with_open_queue()
            return len(doctors_with_open_queue) > 0
        finally:
            db.close()

    def get_doctors_with_open_queue(self) -> List[User]:
        """Get doctors who have queue open, telemedicine access, and Google Calendar enabled."""
        db_session = self.get_db_session()
        try:
            doctors = (
                db_session.query(User)
                .filter(
                    User.role == "doctor",
                    User.queue_open == True,
                    User.telemedicine_access == True,
                    User.google_calendar_enabled == True,  # Must have Google Calendar connected
                )
                .all()
            )
            return doctors
        finally:
            db_session.close()

    def add_to_queue(self, patient_id: int):
        db_session = self.get_db_session()
        try:
            user = db_session.query(User).filter(User.id == patient_id).first()
            
            if not user:
                raise Exception(f"Patient with ID {patient_id} not found")
            
            # Check if patient is already waiting
            if user.queue_status == "waiting":
                # Already in queue, do nothing
                return
            
            # Update user status in DB (primary source of truth)
            user.queue_status = "waiting"
            user.queue_entry_time = datetime.now()
            db_session.commit()
            db_session.refresh(user)
            
            # If Redis is available, also add to Redis queue
            if self.redis_enabled and self.redis:
                try:
                    if not self.redis.lpos(self.queue_name, patient_id):
                        self.redis.rpush(self.queue_name, patient_id)
                except Exception as e:
                    # Log but don't fail if Redis operation fails
                    print(f"Warning: Failed to add patient to Redis queue: {e}")
        except Exception as e:
            db_session.rollback()
            raise Exception(f"Failed to add patient to queue: {e}") from e
        finally:
            db_session.close()

    def remove_from_queue(
        self, patient_id: int, status: str = "completed"
    ):  # Added status parameter
        db_session = self.get_db_session()
        try:
            # Update user status in DB (primary source of truth)
            user = db_session.query(User).filter(User.id == patient_id).first()
            if user:
                user.queue_status = (
                    status  # e.g., 'completed', 'no_wait', 'cancelled', 'in_service'
                )
                # Clear queue_entry_time if status is not 'waiting'
                if status != "waiting":
                    user.queue_entry_time = None
                db_session.commit()
                db_session.refresh(user)
            else:
                raise Exception(f"Patient with ID {patient_id} not found")

            # If Redis is available, also remove from Redis queue
            if self.redis_enabled and self.redis:
                try:
                    self.redis.lrem(self.queue_name, 0, patient_id)
                except Exception as e:
                    # Log but don't fail if Redis operation fails
                    print(f"Warning: Failed to remove patient from Redis queue: {e}")
        except Exception as e:
            db_session.rollback()
            raise Exception(f"Failed to remove patient from queue: {e}") from e
        finally:
            db_session.close()

    def get_queue(self) -> List[int]:
        """
        Returns the list of patient IDs currently in the queue.
        Uses database as the primary source of truth, ordered by queue_entry_time.
        If Redis is available, it's kept in sync but DB is authoritative.
        """
        db_session = self.get_db_session()
        try:
            # Query database for users with 'waiting' status, ordered by entry time
            waiting_patients = (
                db_session.query(User.id)
                .filter(User.queue_status == "waiting")
                .order_by(User.queue_entry_time)
                .all()
            )
            # Extract patient IDs
            patient_ids = [patient.id for patient in waiting_patients]
            
            # If Redis is available, try to sync it (but don't fail if it doesn't work)
            if self.redis_enabled and self.redis:
                try:
                    # Sync Redis with DB state
                    redis_queue = [
                        int(pid) for pid in self.redis.lrange(self.queue_name, 0, -1)
                    ]
                    # Add any missing IDs to Redis
                    for pid in patient_ids:
                        if pid not in redis_queue:
                            self.redis.rpush(self.queue_name, pid)
                    # Remove any IDs from Redis that are not in DB
                    for pid in redis_queue:
                        if pid not in patient_ids:
                            self.redis.lrem(self.queue_name, 0, pid)
                except Exception as e:
                    # Log but don't fail if Redis sync fails
                    print(f"Warning: Failed to sync Redis queue: {e}")
            
            return patient_ids
        except Exception as e:
            raise Exception(f"Failed to retrieve queue: {e}") from e
        finally:
            db_session.close()

    # --- New methods based on DOCTOR_BACKEND.md ---

    def get_queue_stats(self) -> dict:
        """Returns a dictionary with all queue-related counts."""
        try:
            waiting_count = self.get_waiting_customers_count()
            in_service_count = len(self.get_customers_in_attendance_with_doctor())
            completed_count = self.get_completed_services_count()
            
            stats = {
                "waiting": waiting_count,
                "in_service": in_service_count,
                "completed": completed_count,
                "total": waiting_count + in_service_count + completed_count,
            }
            return stats
        except Exception as e:
            raise Exception(f"Failed to retrieve queue stats: {e}") from e

    def get_customers_in_attendance_with_doctor(self) -> List[dict]:
        """Shows the list of customers in attendance with the name of the professional who is currently assisting the customer."""
        db_session = self.get_db_session()
        try:
            # Query for telemedicine sessions that are 'in_progress'
            # Join with User table for patient details (name)
            # Join with User table again for doctor details (name)

            sessions_in_progress = (
                db_session.query(
                    TelemedicineSession.id,
                    TelemedicineSession.patient_id,
                    TelemedicineSession.doctor_id,
                    TelemedicineSession.started_at,
                    TelemedicineSession.meet_call_link,
                    User.name.label("patient_name"),
                    User.queue_status,  # Include patient's queue status
                    User.queue_entry_time,  # Include patient's queue entry time
                )
                .join(User, TelemedicineSession.patient_id == User.id)
                .filter(TelemedicineSession.status == "in_progress")
                .all()
            )

            results = []
            for session in sessions_in_progress:
                # Fetch doctor's name by doctor_id
                doctor = db_session.query(User).filter(User.id == session.doctor_id).first()
                doctor_name = doctor.name if doctor else "Unknown Doctor"

                results.append(
                    {
                        "session_id": session.id,
                        "patient_id": session.patient_id,
                        "patient_name": session.patient_name,
                        "doctor_id": session.doctor_id,
                        "doctor_name": doctor_name,
                        "queue_status": session.queue_status,  # Patient's current queue status
                        "queue_entry_time": session.queue_entry_time.isoformat() if session.queue_entry_time else None,  # Patient's queue entry time
                        "service_start_time": session.started_at.isoformat() if session.started_at else None,  # When the service started
                        "meet_call_link": session.meet_call_link,
                    }
                )

            return results
        finally:
            db_session.close()

    def get_completed_services_count(self) -> int:
        """Shows the total number of services already carried out with completed status."""
        db_session = self.get_db_session()
        try:
            count = db_session.query(User).filter(User.queue_status == "completed").count()
            return count
        finally:
            db_session.close()

    def get_no_wait_services_count(self) -> int:
        """Shows the total number of people who entered the service queue but did not wait to be served."""
        db_session = self.get_db_session()
        try:
            count = db_session.query(User).filter(User.queue_status == "no_wait").count()
            return count
        finally:
            db_session.close()

    def get_waiting_customers_count(self) -> int:
        """Shows the total number of customers in the queue waiting for the appointment to begin."""
        db_session = self.get_db_session()
        try:
            count = db_session.query(User).filter(User.queue_status == "waiting").count()
            return count
        finally:
            db_session.close()

    def get_next_patient(self) -> Optional[User]:
        """Gets the next patient from the 'waiting' queue, ordered by entry time."""
        db_session = self.get_db_session()
        try:
            # Query for users with 'waiting' status, ordered by their entry time
            next_patient = (
                db_session.query(User)
                .filter(User.queue_status == "waiting")
                .order_by(User.queue_entry_time)
                .first()
            )
            return next_patient
        finally:
            db_session.close()

    def update_patient_status(
        self, patient_id: int, new_status: str, doctor_id: Optional[int] = None
    ):
        """Updates a patient's queue status and optionally assigns a doctor (indirectly via Appointment)."""
        db_session = self.get_db_session()
        try:
            user = db_session.query(User).filter(User.id == patient_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="Patient not found")

            user.queue_status = new_status
            if new_status != "waiting":  # Clear entry time if status is not 'waiting'
                user.queue_entry_time = None

            # If moving to 'in_service', this method itself doesn't create the Appointment.
            # That's handled by call_next_patient. This method just updates the User status.

            db_session.commit()
            db_session.refresh(user)
        except Exception as e:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    def call_next_patient(self, doctor_id: int) -> dict:
        """
        Doctor initiates call for the next client in line.
        Creates a TelemedicineSession and generates a Google Meet link.
        """
        db_session = self.get_db_session()
        session_service = TelemedicineSessionService()
        try:
            # 1. Get the next patient from the waiting queue (ordered by DB entry time)
            next_patient = (
                db_session.query(User)
                .filter(User.queue_status == "waiting")
                .order_by(User.queue_entry_time)
                .first()
            )

            if not next_patient:
                raise HTTPException(
                    status_code=404, detail="No patients waiting in the queue."
                )

            # 2. Get doctor details
            doctor = db_session.query(User).filter(User.id == doctor_id).first()
            if not doctor:
                raise HTTPException(status_code=404, detail="Doctor not found")
            
            # 2.1. Check if doctor has Google Calendar enabled
            if not doctor.google_calendar_enabled:
                raise HTTPException(
                    status_code=400,
                    detail="Doctor must connect Google Calendar to use telemedicine. Please connect your Google Calendar in settings."
                )

            # 3. Update patient's status to 'in_service' in the User table
            next_patient.queue_status = "in_service"
            next_patient.queue_entry_time = None  # Clear entry time
            db_session.commit()
            db_session.refresh(next_patient)

            # 4. If Redis is available, remove patient from Redis queue to keep it in sync
            if self.redis_enabled and self.redis:
                try:
                    self.redis.lrem(self.queue_name, 0, next_patient.id)
                except Exception as e:
                    print(
                        f"Warning: Failed to remove patient {next_patient.id} from Redis queue: {e}"
                    )

            # 5. Create Google Meet link using doctor's Google credentials
            meet_call_link = None
            try:
                meet_service = GoogleMeetService(doctor_id=doctor_id, db=db_session)
                start_time = datetime.utcnow()
                end_time = start_time + timedelta(hours=1)
                meet_call_link = meet_service.create_meeting(
                    summary=f"Telemedicine Consultation - {next_patient.name}",
                    start_time=start_time,
                    end_time=end_time,
                    attendees=[doctor.email, next_patient.email],
                )
            except Exception as e:
                # Log error but continue - create session without meet link
                print(f"Warning: Failed to create Google Meet link: {e}")
                meet_call_link = None

            # 6. Create TelemedicineSession record
            new_session = session_service.create_session(
                patient_id=next_patient.id,
                doctor_id=doctor_id,
                meet_call_link=meet_call_link,
            )

            return {
                "message": f"Calling next patient: {next_patient.name} (ID: {next_patient.id}) for Doctor ID: {doctor_id}",
                "session_id": new_session.id,
                "patient_id": next_patient.id,
                "patient_name": next_patient.name,
                "doctor_id": doctor_id,
                "meet_call_link": meet_call_link or f"https://meet.example.com/{next_patient.id}_{doctor_id}_{new_session.id}",
            }
        except HTTPException:
            db_session.rollback()
            raise
        except Exception as e:
            db_session.rollback()
            raise Exception(f"Failed to call next patient: {e}") from e
        finally:
            db_session.close()

    def get_waiting_customers_details(self) -> List[dict]:
        """Shows the list of customers waiting for service with detailed information."""
        db_session = self.get_db_session()
        try:
            # Query for users with 'waiting' status, ordered by their entry time
            waiting_patients = (
                db_session.query(User)
                .filter(User.queue_status == "waiting")
                .order_by(User.queue_entry_time)
                .all()
            )

            results = []
            for patient in waiting_patients:
                # Determine online/offline status. This is a placeholder.
                # In a real app, this would come from a presence system or last seen timestamp.
                # For now, we'll assume 'online' if they are in the 'waiting' status.
                online_status = "online"  # Placeholder for online/offline status

                results.append(
                    {
                        "patient_id": patient.id,
                        "patient_name": patient.name,
                        "queue_entry_time": patient.queue_entry_time.isoformat() if patient.queue_entry_time else None,
                        "status": patient.queue_status,  # Should be 'waiting'
                        "online_status": online_status,
                    }
                )
            return results
        finally:
            db_session.close()

    def get_queue_with_details(self) -> List[dict]:
        """
        Returns the list of patients in the queue with full details including:
        - id: patient ID
        - name: patient name
        - queue_entry_time: when they joined the queue
        """
        db_session = self.get_db_session()
        try:
            # Query database for users with 'waiting' status, ordered by entry time
            waiting_patients = (
                db_session.query(User)
                .filter(User.queue_status == "waiting")
                .order_by(User.queue_entry_time)
                .all()
            )
            
            # Build result list with patient details
            result = []
            for patient in waiting_patients:
                result.append({
                    "id": patient.id,
                    "name": patient.name,
                    "queue_entry_time": patient.queue_entry_time.isoformat() if patient.queue_entry_time else None,
                })
            
            return result
        except Exception as e:
            raise Exception(f"Failed to retrieve queue with details: {e}") from e
        finally:
            db_session.close()
