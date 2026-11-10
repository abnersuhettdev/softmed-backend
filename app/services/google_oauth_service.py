import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import requests
from dotenv import load_dotenv

from app.services.encryption_service import EncryptionService

load_dotenv()


class GoogleOAuthService:
    """
    Service for handling Google OAuth 2.0 authentication flow.
    Handles authorization URL generation, token exchange, user info retrieval, and token refresh.
    """
    
    # Class-level state token storage (shared across all instances)
    # In production, use Redis with TTL instead
    _state_tokens: Dict[str, float] = {}
    
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
        self.frontend_url = os.getenv("FRONTEND_DOCTOR_BASE_URL", "http://localhost:5173")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in environment variables")
        
        # OAuth endpoints
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        
        # Required scopes
        self.scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ]
        
        self._encryption_service = None  # Lazy load to avoid errors during OAuth initiation
    
    def generate_authorization_url(self, state: str) -> str:
        """
        Generate Google OAuth authorization URL.
        
        Args:
            state: CSRF protection token
            
        Returns:
            Authorization URL
            
        Note: If you see "Google hasn't verified this app" warning:
        - This is normal for apps in testing mode
        - Add test users in Google Cloud Console: APIs & Services > Credentials > OAuth 2.0 Client ID > Test users
        - Or click "Continue" if you're the developer
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",  # Required to get refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
            "state": state,
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_url}?{query_string}"
    
    def generate_state_token(self) -> str:
        """
        Generate a random state token for CSRF protection.
        
        Returns:
            Random state token
        """
        return secrets.token_urlsafe(32)
    
    def store_state_token(self, state: str, expires_in_minutes: int = 10, frontend_url: Optional[str] = None):
        """
        Store state token with expiration time and optional frontend URL.
        
        Args:
            state: State token to store
            expires_in_minutes: Expiration time in minutes (default 10)
            frontend_url: Optional frontend URL to store with state
        """
        expires_at = time.time() + (expires_in_minutes * 60)
        GoogleOAuthService._state_tokens[state] = {
            "expires_at": expires_at,
            "frontend_url": frontend_url
        }
        
        # Clean up expired tokens (simple cleanup)
        current_time = time.time()
        expired_states = []
        for s, data in GoogleOAuthService._state_tokens.items():
            expires_at = data.get("expires_at") if isinstance(data, dict) else data
            if expires_at < current_time:
                expired_states.append(s)
        for expired_state in expired_states:
            del GoogleOAuthService._state_tokens[expired_state]
    
    def verify_state_token(self, state: str) -> tuple[bool, Optional[str]]:
        """
        Verify and remove state token (one-time use).
        
        Args:
            state: State token to verify
            
        Returns:
            Tuple of (is_valid, frontend_url)
        """
        if state not in GoogleOAuthService._state_tokens:
            print(f"State token not found. Available tokens: {list(GoogleOAuthService._state_tokens.keys())[:5]}...")
            return False, None
        
        state_data = GoogleOAuthService._state_tokens[state]
        
        # Handle old format (just expires_at) for backward compatibility
        if isinstance(state_data, (int, float)):
            expires_at = state_data
            frontend_url = None
        else:
            expires_at = state_data.get("expires_at")
            frontend_url = state_data.get("frontend_url")
        
        current_time = time.time()
        
        if current_time > expires_at:
            # Token expired
            del GoogleOAuthService._state_tokens[state]
            print(f"State token expired. Current time: {current_time}, Expires at: {expires_at}")
            return False, None
        
        # Token is valid, remove it (one-time use)
        del GoogleOAuthService._state_tokens[state]
        print(f"State token verified successfully")
        return True, frontend_url
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, any]:
        """
        Exchange authorization code for access token and refresh token.
        
        Args:
            code: Authorization code from Google
            
        Returns:
            Dictionary with access_token, refresh_token, expires_in, etc.
            
        Raises:
            Exception: If token exchange fails
        """
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        
        response = requests.post(self.token_url, data=data)
        
        if response.status_code != 200:
            error_data = response.json()
            raise Exception(f"Failed to exchange code for tokens: {error_data.get('error_description', 'Unknown error')}")
        
        return response.json()
    
    def get_google_user_info(self, access_token: str) -> Dict[str, any]:
        """
        Get user information from Google UserInfo API.
        
        Args:
            access_token: Google OAuth access token
            
        Returns:
            Dictionary with user info (email, name, picture, etc.)
            
        Raises:
            Exception: If API call fails
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(self.userinfo_url, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get user info: {response.text}")
        
        return response.json()
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, any]:
        """
        Refresh an expired access token using refresh token.
        
        Args:
            refresh_token: Google OAuth refresh token
            
        Returns:
            Dictionary with new access_token, expires_in, etc.
            
        Raises:
            Exception: If token refresh fails
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        response = requests.post(self.token_url, data=data)
        
        if response.status_code != 200:
            error_data = response.json()
            raise Exception(f"Failed to refresh token: {error_data.get('error_description', 'Unknown error')}")
        
        return response.json()
    
    @property
    def encryption_service(self):
        """Lazy load encryption service to avoid initialization errors during OAuth."""
        if self._encryption_service is None:
            self._encryption_service = EncryptionService()
        return self._encryption_service
    
    def encrypt_token(self, token: str) -> str:
        """
        Encrypt a token before storing in database.
        
        Args:
            token: Plaintext token
            
        Returns:
            Encrypted token
        """
        return self.encryption_service.encrypt(token)
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt a token from database.
        
        Args:
            encrypted_token: Encrypted token
            
        Returns:
            Decrypted plaintext token
        """
        return self.encryption_service.decrypt(encrypted_token)
    
    def calculate_token_expiry(self, expires_in: int) -> datetime:
        """
        Calculate token expiry datetime from expires_in seconds.
        
        Args:
            expires_in: Number of seconds until token expires
            
        Returns:
            Datetime when token expires
        """
        return datetime.utcnow() + timedelta(seconds=expires_in)

