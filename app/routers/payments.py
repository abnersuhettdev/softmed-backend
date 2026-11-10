from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.payments import (CreatePaymentIntentRequest,
                                  PaymentIntentResponse)
from app.schemas.pix import CreatePixPaymentRequest, PixPaymentResponse
from app.services.payment_service import PaymentService
from app.services.pix_service import create_pix_payment

router = APIRouter()


@router.post("/create-payment-intent", response_model=PaymentIntentResponse)
def create_payment_intent(
    request: CreatePaymentIntentRequest, payment_service: PaymentService = Depends()
):
    try:
        response = payment_service.create_payment_intent(request.amount)
        if "error" in response:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=response["error"]
            )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment intent: {e}",
        )


@router.post("/create-pix-payment", response_model=PixPaymentResponse)
def create_pix_payment_endpoint(
    request: CreatePixPaymentRequest, db: Session = Depends(get_db)
):
    try:
        # For now, we'll use a hardcoded user_id. In a real application, this would come from authentication.
        user_id = 1  # Replace with actual authenticated user ID
        payment = create_pix_payment(db, user_id, request.amount, request.description)
        return PixPaymentResponse(
            pix_transaction_id=payment.pix_transaction_id,
            pix_qr_code_data=payment.pix_qr_code_data,
            pix_status=payment.pix_status,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create PIX payment: {e}",
        )
