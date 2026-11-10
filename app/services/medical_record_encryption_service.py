import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

load_dotenv()


class MedicalRecordEncryptionService:
    """
    Service for encrypting and decrypting medical records using AES-256-GCM.
    Provides authenticated encryption with additional data (AEAD).
    """
    
    def __init__(self):
        # Get encryption key from environment variable (must be 32 bytes for AES-256)
        encryption_key = os.getenv("MEDICAL_RECORD_ENCRYPTION_KEY")
        
        if not encryption_key:
            raise ValueError(
                "MEDICAL_RECORD_ENCRYPTION_KEY environment variable is required. "
                "Generate one using: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        
        # Convert hex string to bytes (if provided as hex)
        if len(encryption_key) == 64:  # 32 bytes = 64 hex characters
            self.key = bytes.fromhex(encryption_key)
        else:
            # If not hex, use as-is (must be exactly 32 bytes)
            if isinstance(encryption_key, str):
                encryption_key = encryption_key.encode()
            if len(encryption_key) != 32:
                raise ValueError(
                    f"MEDICAL_RECORD_ENCRYPTION_KEY must be exactly 32 bytes (64 hex characters). "
                    f"Got {len(encryption_key)} bytes."
                )
            self.key = encryption_key
        
        self.aesgcm = AESGCM(self.key)
    
    def encrypt(self, plaintext: str) -> dict:
        """
        Encrypt medical record text using AES-256-GCM.
        
        Args:
            plaintext: The medical record text to encrypt
            
        Returns:
            Dictionary containing:
            - encryptedData: Base64-encoded encrypted data
            - iv: Base64-encoded initialization vector (12 bytes for GCM)
            - authTag: Base64-encoded authentication tag (16 bytes for GCM)
        """
        if not plaintext:
            return {
                "encryptedData": "",
                "iv": "",
                "authTag": ""
            }
        
        # Generate random IV (12 bytes for GCM)
        iv = os.urandom(12)
        
        # Encrypt the plaintext
        ciphertext = self.aesgcm.encrypt(iv, plaintext.encode('utf-8'), None)
        
        # GCM returns ciphertext + auth_tag concatenated
        # Auth tag is the last 16 bytes
        encrypted_data = ciphertext[:-16]
        auth_tag = ciphertext[-16:]
        
        return {
            "encryptedData": base64.b64encode(encrypted_data).decode('utf-8'),
            "iv": base64.b64encode(iv).decode('utf-8'),
            "authTag": base64.b64encode(auth_tag).decode('utf-8')
        }
    
    def decrypt(self, encrypted_data: str, iv: str, auth_tag: str) -> str:
        """
        Decrypt medical record text using AES-256-GCM.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            iv: Base64-encoded initialization vector
            auth_tag: Base64-encoded authentication tag
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            ValueError: If decryption fails (authentication failed)
        """
        if not encrypted_data or not iv or not auth_tag:
            return ""
        
        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            iv_bytes = base64.b64decode(iv)
            auth_tag_bytes = base64.b64decode(auth_tag)
            
            # Reconstruct ciphertext (encrypted_data + auth_tag)
            ciphertext = encrypted_bytes + auth_tag_bytes
            
            # Decrypt
            plaintext_bytes = self.aesgcm.decrypt(iv_bytes, ciphertext, None)
            
            return plaintext_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

