import os
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()


class MevoService:
    """
    Service for integrating with Mevo electronic prescription API.
    """
    
    def __init__(self):
        self.api_base_url = os.getenv("MEVO_API_BASE_URL", "https://api.mevo.com.br/v1")
        self.api_key = os.getenv("MEVO_API_KEY")
        self.api_secret = os.getenv("MEVO_API_SECRET")
        
        if not self.api_key:
            raise ValueError("MEVO_API_KEY environment variable is required")
    
    def create_prescription(
        self,
        patient_id: int,
        patient_name: str,
        patient_cpf: str,
        doctor_id: int,
        doctor_crm: str,
        doctor_cpf: str,
        doctor_name: str,
        medications: List[Dict[str, Any]],
        consultation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create an electronic prescription via Mevo API.
        
        Args:
            patient_id: Patient's ID in our system
            patient_name: Patient's full name
            patient_cpf: Patient's CPF
            doctor_id: Doctor's ID in our system
            doctor_crm: Doctor's CRM number
            doctor_cpf: Doctor's CPF
            doctor_name: Doctor's full name
            medications: List of medications, each containing:
                - name: Medication name
                - dosage: Dosage information
                - quantity: Quantity
                - instructions: Usage instructions
            consultation_id: Optional consultation/session ID
            
        Returns:
            Dictionary containing prescription metadata:
            - prescription_id: Mevo prescription ID
            - prescription_token: Token for accessing prescription
            - created_at: Timestamp
            - pdf_url: URL to prescription PDF (if available)
        """
        # Prepare prescription request payload
        # Note: This is a placeholder structure. Actual API may differ.
        # Consult Mevo API documentation for exact endpoint and payload format.
        payload = {
            "patient": {
                "id": patient_id,
                "name": patient_name,
                "cpf": patient_cpf
            },
            "prescriber": {
                "id": doctor_id,
                "crm": doctor_crm,
                "cpf": doctor_cpf,
                "name": doctor_name
            },
            "medications": medications,
            "metadata": {
                "consultation_id": consultation_id,
                "created_at": datetime.utcnow().isoformat()
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key
        }
        
        if self.api_secret:
            headers["X-API-Secret"] = self.api_secret
        
        try:
            # Placeholder endpoint - replace with actual Mevo API endpoint
            response = requests.post(
                f"{self.api_base_url}/prescriptions",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            response_data = response.json()
            
            # Extract prescription metadata from response
            # Adjust these fields based on actual Mevo API response structure
            return {
                "prescription_id": response_data.get("id") or response_data.get("prescription_id"),
                "prescription_token": response_data.get("token") or response_data.get("prescription_token"),
                "created_at": datetime.utcnow().isoformat(),
                "pdf_url": response_data.get("pdf_url"),
                "mevo_response": response_data  # Store full response for debugging
            }
        except requests.exceptions.RequestException as e:
            raise Exception(f"Mevo API error: {str(e)}")
    
    def get_prescription(self, prescription_id: str) -> Dict[str, Any]:
        """
        Retrieve prescription details from Mevo API.
        
        Args:
            prescription_id: Mevo prescription ID
            
        Returns:
            Dictionary containing prescription details
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key
        }
        
        if self.api_secret:
            headers["X-API-Secret"] = self.api_secret
        
        try:
            response = requests.get(
                f"{self.api_base_url}/prescriptions/{prescription_id}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Mevo API error: {str(e)}")

