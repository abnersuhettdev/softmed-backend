import os
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv

load_dotenv()


class MemedService:
    def __init__(self):
        self.api_key = os.getenv("MEMED_API_KEY")
        if self.api_key is None:
            raise Exception("MEMED_API_KEY environment variable is not set.")
        self.base_url = "https://api.memed.com.br/v1"
        self.token = self._get_token()

    def _get_token(self):
        # This is a simplified example. In a real application, you would
        # handle token expiration and renewal.
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": "memed",
            "client_secret": self.api_key,
        }
        try:
            response = httpx.post(
                f"{self.base_url}/auth/token", headers=headers, data=data
            )
            response.raise_for_status()
            return response.json()["access_token"]
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to get Memed API token: {e.response.text}") from e
        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to Memed API: {e}") from e

    def create_prescription(self, patient_name: str, medicines: List[Dict[str, Any]]):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        data = {
            "patient": {"name": patient_name},
            "medicines": medicines,
        }
        try:
            response = httpx.post(
                f"{self.base_url}/prescricao", headers=headers, json=data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise Exception(
                f"Failed to create Memed prescription: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to Memed API: {e}") from e
