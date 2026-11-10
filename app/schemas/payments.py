from pydantic import BaseModel


class CreatePaymentIntentRequest(BaseModel):
    amount: int


class PaymentIntentResponse(BaseModel):
    client_secret: str
