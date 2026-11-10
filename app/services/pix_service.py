import os
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from app.models.payment import Payment

load_dotenv()  # Load environment variables

PAGARME_SECRET_KEY = os.getenv("PAGARME_SECRET_KEY")
PAGARME_API_URL = os.getenv(
    "PAGARME_API_URL", "https://api.pagar.me/core/v5"
)  # Default to v5 API URL


class PagarmeAPI:
    def __init__(self):
        if not PAGARME_SECRET_KEY:
            raise ValueError("PAGARME_SECRET_KEY environment variable not set.")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {PAGARME_SECRET_KEY}",  # Pagar.me uses Basic Auth with secret key
        }

    def create_pix_charge(self, amount: int, description: str):
        # In a real application, you would create a customer and order first.
        # For simplicity, we're directly creating a charge here.
        # Refer to Pagar.me API documentation for full flow.

        endpoint = f"{PAGARME_API_URL}/charges"
        payload = {
            "amount": amount,  # Amount in cents
            "payment_method": "pix",
            "pix": {
                "expires_in": 3600,  # PIX QR Code valid for 1 hour (in seconds)
            },
            "description": description,
            # You would typically include customer information here
            # "customer": {
            #     "name": "Customer Name",
            #     "email": "customer@example.com",
            #     "document": "11111111111",
            #     "type": "individual"
            # }
        }

        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            response_data = response.json()

            # Extract relevant PIX data from Pagar.me response
            # This structure might vary based on Pagar.me API version and response
            # Assuming a structure like: response_data['charges'][0]['last_transaction']['qr_code']
            charge_data = response_data.get("charges", [{}])[0]
            last_transaction = charge_data.get("last_transaction", {})
            pix_data = last_transaction.get("qr_code", {})

            pix_transaction_id = charge_data.get("id")
            pix_qr_code_data = pix_data.get("qr_code_url")  # Or qr_code_base64
            pix_status = charge_data.get("status")

            return {
                "pix_transaction_id": pix_transaction_id,
                "pix_qr_code_data": pix_qr_code_data,
                "pix_status": pix_status,
            }
        except requests.exceptions.RequestException as e:
            print(f"Pagar.me API request failed: {e}")
            raise
        except Exception as e:
            print(f"Error processing Pagar.me response: {e}")
            raise


# Lazy initialization - only create when needed
_pagarme_api = None

def get_pagarme_api():
    global _pagarme_api
    if _pagarme_api is None:
        _pagarme_api = PagarmeAPI()
    return _pagarme_api


def create_pix_payment(db: Session, user_id: int, amount: int, description: str):
    # 1. Create PIX charge via Pagar.me API
    pagarme_api = get_pagarme_api()
    pix_charge_data = pagarme_api.create_pix_charge(amount, description)

    # 2. Create a new Payment record in the database
    new_payment = Payment(
        user_id=user_id,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=30),  # Example: 30-day subscription
        pix_transaction_id=pix_charge_data["pix_transaction_id"],
        pix_qr_code_data=pix_charge_data["pix_qr_code_data"],
        pix_status=pix_charge_data["pix_status"],
    )
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)
    return new_payment
