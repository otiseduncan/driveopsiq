#!/usr/bin/env python3
"""
Test script to generate a token and test the /me endpoint
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.security import create_access_token

def test_token_generation():
    """Test token generation with email as subject."""
    
    # Test with email as subject (new way)
    email = "otiseduncan@gmail.com"
    
    print("🔧 Testing token generation...")
    print(f"📧 Using email as subject: {email}")
    
    # Create token with email as subject
    access_token = create_access_token(subject=email)
    
    print(f"🎟️  Generated access token:")
    print(f"   {access_token}")
    print()
    print("🧪 Test this token with curl:")
    print(f'curl -H "Authorization: Bearer {access_token}" http://localhost:8001/api/v1/users/me')
    print()
    
    return access_token

if __name__ == "__main__":
    test_token_generation()