from fastapi import APIRouter, Depends, HTTPException, status

from app.services.memed_service import MemedService

router = APIRouter()

from app.schemas.prescription import CreatePrescriptionRequest


@router.post("/")
def create_prescription(
    request: CreatePrescriptionRequest, memed_service: MemedService = Depends()
):
    try:
        prescription = memed_service.create_prescription(
            request.patient_name, request.medicines
        )
        return prescription
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Memed prescription: {e}",
        )
