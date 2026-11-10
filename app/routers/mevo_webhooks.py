"""
Mevo Webhook Endpoints

Handles webhook events from Mevo platform:
- EMISSION: When a prescription is finalized
- CANCEL: When a prescription is canceled
"""
from fastapi import APIRouter, HTTPException, status, Header, Depends
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import os

from app.database import get_db
from app.models.medical_record import MedicalRecord as MedicalRecordModel
from app.models.user import User as UserModel
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()


class MevoEmissionPayload(BaseModel):
    """Payload structure for EMISSION webhook event"""
    idPrescricaoStatus: int
    idPrescricao: int
    CodigoValidacao: Optional[str] = None
    CertificadoDigitalObrigatorio: Optional[bool] = False
    TemBeneficio: Optional[bool] = False
    ReferenciaInterna: Optional[str] = None
    DataCriacao: Optional[str] = None
    PrescricaoAssinada: Optional[bool] = False
    PDFUrl: Optional[str] = None
    ExamePDFUrl: Optional[str] = None
    AtestadoPDFUrl: Optional[str] = None
    # Add other fields as needed based on actual webhook payload


class MevoCancelPayload(BaseModel):
    """Payload structure for CANCEL webhook event"""
    idPrescricao: int


def verify_webhook_auth(authorization: Optional[str] = Header(None)) -> bool:
    """
    Verify webhook authentication using Authorization header.
    Expected format: "Bearer {token}" or "Basic {credentials}"
    """
    if not authorization:
        return False
    
    # Get expected auth token from environment
    expected_token = os.getenv("MEVO_WEBHOOK_AUTH_TOKEN")
    if not expected_token:
        # If no token configured, allow (for development)
        return True
    
    # Check if authorization matches expected format
    if authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        return token == expected_token
    elif authorization.startswith("Basic "):
        credentials = authorization.replace("Basic ", "")
        return credentials == expected_token
    
    return False


@router.post("/emission", status_code=status.HTTP_201_CREATED)
async def handle_emission_webhook(
    payload: MevoEmissionPayload,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Handle EMISSION webhook event from Mevo.
    This is called when a prescription is finalized.
    
    Expected response: HTTP 201 Created
    """
    # Verify webhook authentication
    if not verify_webhook_auth(authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook authentication"
        )
    
    try:
        # Find medical record by ReferenciaInterna (consultation/session ID)
        # or by prescription_id if already linked
        record = None
        
        if payload.ReferenciaInterna:
            # Try to find by consultation_id or session_id
            consultation_id = None
            session_id = None
            try:
                if payload.ReferenciaInterna.startswith("consultation_"):
                    consultation_id = int(payload.ReferenciaInterna.replace("consultation_", ""))
                elif payload.ReferenciaInterna.startswith("session_"):
                    session_id = int(payload.ReferenciaInterna.replace("session_", ""))
            except ValueError:
                pass
            
            if consultation_id:
                record = db.query(MedicalRecordModel).filter(
                    MedicalRecordModel.consultation_id == consultation_id
                ).first()
            elif session_id:
                record = db.query(MedicalRecordModel).filter(
                    MedicalRecordModel.session_id == session_id
                ).first()
        
        # If not found by reference, try by prescription_id
        if not record and payload.idPrescricao:
            record = db.query(MedicalRecordModel).filter(
                MedicalRecordModel.prescription_id == str(payload.idPrescricao)
            ).first()
        
        if record:
            # Update medical record with prescription data
            record.prescription_id = str(payload.idPrescricao)
            record.prescription_token = payload.CodigoValidacao
            record.prescription_metadata = {
                "idPrescricaoStatus": payload.idPrescricaoStatus,
                "idPrescricao": payload.idPrescricao,
                "CodigoValidacao": payload.CodigoValidacao,
                "PrescricaoAssinada": payload.PrescricaoAssinada,
                "PDFUrl": payload.PDFUrl,
                "ExamePDFUrl": payload.ExamePDFUrl,
                "AtestadoPDFUrl": payload.AtestadoPDFUrl,
                "DataCriacao": payload.DataCriacao,
                "webhook_received_at": datetime.utcnow().isoformat(),
                "full_payload": payload.dict()  # Store full payload for reference
            }
            
            db.commit()
            db.refresh(record)
        
        # Return 201 Created as required by Mevo
        return {
            "status": "success",
            "message": "Prescription emission webhook processed",
            "idPrescricao": payload.idPrescricao
        }
    
    except Exception as e:
        # Log error but return 201 to prevent retries
        # Mevo will retry if we return non-201 status
        print(f"Error processing Mevo EMISSION webhook: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "idPrescricao": payload.idPrescricao
        }


@router.post("/cancel", status_code=status.HTTP_201_CREATED)
async def handle_cancel_webhook(
    payload: MevoCancelPayload,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Handle CANCEL webhook event from Mevo.
    This is called when a prescription is canceled/deleted.
    
    Expected response: HTTP 201 Created
    """
    # Verify webhook authentication
    if not verify_webhook_auth(authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook authentication"
        )
    
    try:
        # Find medical record by prescription_id
        record = db.query(MedicalRecordModel).filter(
            MedicalRecordModel.prescription_id == str(payload.idPrescricao)
        ).first()
        
        if record:
            # Update prescription metadata to indicate cancellation
            if record.prescription_metadata:
                record.prescription_metadata["canceled"] = True
                record.prescription_metadata["canceled_at"] = datetime.utcnow().isoformat()
            else:
                record.prescription_metadata = {
                    "canceled": True,
                    "canceled_at": datetime.utcnow().isoformat()
                }
            
            # Optionally clear prescription_id to indicate it's no longer valid
            # Or keep it for audit purposes
            # record.prescription_id = None
            
            db.commit()
            db.refresh(record)
        
        # Return 201 Created as required by Mevo
        return {
            "status": "success",
            "message": "Prescription cancellation webhook processed",
            "idPrescricao": payload.idPrescricao
        }
    
    except Exception as e:
        # Log error but return 201 to prevent retries
        print(f"Error processing Mevo CANCEL webhook: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "idPrescricao": payload.idPrescricao
        }

