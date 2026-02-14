#!/usr/bin/env python
"""
Generate encryption keys for IshemaLink API.
Run this ONCE during deployment setup.

Usage:
    python generate_keys.py
"""

from cryptography.fernet import Fernet
import secrets

def generate_fernet_key() -> str:
    """Generate Fernet encryption key for field-level encryption."""
    key = Fernet.generate_key()
    return key.decode('utf-8')

def generate_django_secret_key() -> str:
    """Generate Django SECRET_KEY."""
    return secrets.token_urlsafe(50)

def main():
    print("=" * 70)
    print("IshemaLink API - Security Keys Generator")
    print("=" * 70)
    print()
    
    print("1. Django SECRET_KEY:")
    print("-" * 70)
    secret_key = generate_django_secret_key()
    print(secret_key)
    print()
    
    print("2. Fernet FIELD_ENCRYPTION_KEY:")
    print("-" * 70)
    fernet_key = generate_fernet_key()
    print(fernet_key)
    print()
    
    print("=" * 70)
    print("IMPORTANT INSTRUCTIONS:")
    print("=" * 70)
    print("1. Copy these keys to your .env file:")
    print(f"   SECRET_KEY={secret_key}")
    print(f"   FIELD_ENCRYPTION_KEY={fernet_key}")
    print()
    print("2. NEVER commit these keys to Git")
    print("3. Store a backup copy in a secure password manager")
    print("4. If you lose FIELD_ENCRYPTION_KEY, encrypted data is UNRECOVERABLE")
    print()
    print("=" * 70)

if __name__ == '__main__':
    main()
