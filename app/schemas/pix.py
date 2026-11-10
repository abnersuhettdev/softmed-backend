from pydantic import BaseModel


class CreatePixPaymentRequest(BaseModel):
    amount: int
    description: str


class PixPaymentResponse(BaseModel):
    pix_transaction_id: str
    pix_qr_code_data: str
    pix_status: str
    message: str = "PIX payment initiated successfully."
