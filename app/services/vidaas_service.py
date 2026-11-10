import os
import requests
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class VidaasService:
    """
    Service for integrating with Vidaas ICP digital signature API.
    Documentation: https://developers.integraicp.com.br/api-reference/icp/v3/index.html#/
    
    Note: Doctors use their own Vidaas certificates and auth tokens.
    This service uses the doctor's auth token, not system credentials.
    """
    
    def __init__(self):
        self.api_base_url = os.getenv("VIDAAS_API_BASE_URL", "https://api.integraicp.com.br/v3")
    
    def sign_document_hash(
        self,
        document_hash: str,
        certificate_id: str,
        user_id: str,
        doctor_auth_token: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sign a document hash using Vidaas ICP with doctor's own certificate.
        
        Args:
            document_hash: SHA-256 hash of the encrypted medical record
            certificate_id: Doctor's Vidaas certificate ID
            user_id: Doctor's Vidaas user ID
            doctor_auth_token: Doctor's Vidaas authentication token
            metadata: Optional metadata (consultationId, doctorName, doctorCRM, timestamp)
            
        Returns:
            Dictionary containing signature metadata:
            - signatureId: Vidaas signature ID
            - signedHash: Signed hash from Vidaas
            - timestamp: Timestamp when signature was created
            - certificateMetadata: Certificate metadata from Vidaas
        """
        # Prepare signature request payload
        payload = {
            "documentHash": document_hash,
            "certificateId": certificate_id,
            "userId": user_id
        }
        
        # Add metadata if provided
        if metadata:
            payload["metadata"] = metadata
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {doctor_auth_token}"
        }
        
        try:
            response = requests.post(
                f"{self.api_base_url}/signature",
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            response_data = response.json()
            
            # Extract signature metadata from response
            return {
                "signatureId": response_data.get("signatureId") or response_data.get("id"),
                "signedHash": response_data.get("signedHash") or response_data.get("hash"),
                "timestamp": response_data.get("timestamp") or datetime.utcnow().isoformat(),
                "certificateMetadata": response_data.get("certificateMetadata") or response_data.get("certificate"),
                "vidaas_response": response_data  # Store full response for debugging
            }
        except requests.exceptions.RequestException as e:
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json().get("message") or error_detail
                except:
                    error_detail = e.response.text or error_detail
            raise Exception(f"Vidaas API error: {error_detail}")
    
    def verify_signature(self, signature_id: str, doctor_auth_token: str) -> Dict[str, Any]:
        """
        Verify a digital signature using Vidaas API.
        
        Args:
            signature_id: The Vidaas signature ID to verify
            doctor_auth_token: Doctor's Vidaas authentication token
            
        Returns:
            Dictionary containing verification result
        """
        headers = {
            "Authorization": f"Bearer {doctor_auth_token}"
        }
        
        try:
            response = requests.get(
                f"{self.api_base_url}/signature/{signature_id}/verify",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            error_detail = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json().get("message") or error_detail
                except:
                    error_detail = e.response.text or error_detail
            raise Exception(f"Vidaas verification error: {error_detail}")
    
    @staticmethod
    def create_document_hash(encrypted_data: str) -> str:
        """
        Create SHA-256 hash of encrypted medical record data.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            Hexadecimal SHA-256 hash string
        """
        # Create hash of the encrypted data
        hash_object = hashlib.sha256(encrypted_data.encode('utf-8'))
        return hash_object.hexdigest()
