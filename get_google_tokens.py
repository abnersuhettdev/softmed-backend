#!/usr/bin/env python3
"""
Script to exchange Google OAuth authorization code for access token and refresh token.
Run this after you get the authorization code from the OAuth callback.
"""

import requests
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Get credentials from environment or prompt
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or input("Enter your Google Client ID: ")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") or input("Enter your Google Client Secret: ")
AUTHORIZATION_CODE = input("Enter the authorization code from the callback URL: ").strip()
REDIRECT_URI = "http://localhost:8000/auth/callback"

url = "https://oauth2.googleapis.com/token"
data = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": AUTHORIZATION_CODE,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code"
}

print("\nExchanging authorization code for tokens...")
response = requests.post(url, data=data)

if response.status_code == 200:
    tokens = response.json()
    print("\n✅ Success! Here are your tokens:\n")
    print("=" * 60)
    print("Add these to your .env file:")
    print("=" * 60)
    print(f"GOOGLE_CLIENT_ID={CLIENT_ID}")
    print(f"GOOGLE_CLIENT_SECRET={CLIENT_SECRET}")
    print(f"GOOGLE_OAUTH_TOKEN={tokens.get('access_token')}")
    print(f"GOOGLE_REFRESH_TOKEN={tokens.get('refresh_token')}")
    print("=" * 60)
    print(f"\nToken expires in: {tokens.get('expires_in')} seconds")
    print(f"Scope: {tokens.get('scope')}")
else:
    print(f"\n❌ Error: {response.status_code}")
    print(response.text)
    sys.exit(1)

