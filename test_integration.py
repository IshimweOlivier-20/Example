#!/usr/bin/env python
"""
Integration Test Script for IshemaLink API Formative 2
Run this after migrations to verify all security features are working.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ishemalink.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import AuditLog, OTPVerification, ShippingTariff
from django.core.cache import cache
from cryptography.fernet import Fernet

User = get_user_model()

def print_header(title: str) -> None:
    """Print formatted test section header."""
    print("\n" + "=" * 60)
    print(f"🔍 {title}")
    print("=" * 60)

def test_models_exist() -> bool:
    """Test 1: Verify all models are created."""
    print_header("Test 1: Models Existence")
    
    try:
        # Check User model
        user_count = User.objects.count()
        print(f"✅ User model accessible (count: {user_count})")
        
        # Check AuditLog model
        audit_count = AuditLog.objects.count()
        print(f"✅ AuditLog model accessible (count: {audit_count})")
        
        # Check OTPVerification model
        otp_count = OTPVerification.objects.count()
        print(f"✅ OTPVerification model accessible (count: {otp_count})")
        
        # Check ShippingTariff model
        tariff_count = ShippingTariff.objects.count()
        print(f"✅ ShippingTariff model accessible (count: {tariff_count})")
        
        return True
    except Exception as e:
        print(f"❌ Model check failed: {e}")
        return False

def test_encryption() -> bool:
    """Test 2: Verify field-level encryption is working."""
    print_header("Test 2: Field-Level Encryption")
    
    try:
        # Create test user with encrypted fields
        test_phone = "+250788999999"
        
        # Clean up if exists
        User.objects.filter(phone=test_phone).delete()
        
        user = User.objects.create_user(
            phone=test_phone,
            password="Test1234!",
            full_name="Encryption Test User",
            nid_number="1199980012345678",
            tax_id="123456789",
            user_type="CUSTOMER"
        )
        
        # Check decryption works in ORM
        decrypted_nid = user.nid_number
        print(f"✅ ORM decryption works: {decrypted_nid}")
        
        # Check that database has ciphertext (not plaintext)
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT nid_number, tax_id FROM users WHERE phone = %s",
                [test_phone]
            )
            row = cursor.fetchone()
            db_nid = row[0]
            db_tax = row[1]
            
            # Verify it's encrypted (should NOT be plaintext)
            if db_nid == "1199980012345678":
                print(f"❌ NID is NOT encrypted in database: {db_nid}")
                return False
            else:
                print(f"✅ NID is encrypted in database: {db_nid[:20]}...")
            
            if db_tax == "123456789":
                print(f"❌ Tax ID is NOT encrypted in database: {db_tax}")
                return False
            else:
                print(f"✅ Tax ID is encrypted in database: {db_tax[:20]}...")
        
        # Clean up
        user.delete()
        
        return True
    except Exception as e:
        print(f"❌ Encryption test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_user_roles() -> bool:
    """Test 3: Verify all user roles are defined."""
    print_header("Test 3: User Roles (RBAC)")
    
    try:
        from core.models import User
        
        expected_roles = ['CUSTOMER', 'AGENT', 'DRIVER', 'ADMIN', 'GOV_OFFICIAL']
        available_roles = [choice[0] for choice in User.USER_TYPE_CHOICES]
        
        print(f"Expected roles: {expected_roles}")
        print(f"Available roles: {available_roles}")
        
        for role in expected_roles:
            if role in available_roles:
                print(f"✅ {role} role defined")
            else:
                print(f"❌ {role} role missing")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Role check failed: {e}")
        return False

def test_permissions() -> bool:
    """Test 4: Verify permission classes exist."""
    print_header("Test 4: Permission Classes")
    
    try:
        from core.permissions import (
            IsSectorAgent,
            IsGovOfficial,
            IsDriver,
            IsVerified,
            IsOwnerOrReadOnly
        )
        
        permissions = [
            'IsSectorAgent',
            'IsGovOfficial',
            'IsDriver',
            'IsVerified',
            'IsOwnerOrReadOnly'
        ]
        
        for perm in permissions:
            print(f"✅ {perm} class imported successfully")
        
        return True
    except Exception as e:
        print(f"❌ Permission import failed: {e}")
        return False

def test_validators() -> bool:
    """Test 5: Verify NID validation."""
    print_header("Test 5: Rwanda NID Validation")
    
    try:
        from core.validators import validate_rwanda_nid
        
        # Valid NIDs (with correct birth year encoding)
        valid_nids = [
            ("1199870012345678", 1998),  # Fixed: 1998 in positions 1-4
            ("1198570078901234", 1985),  # Correct
            ("1200010012345678", 2000),  # Correct
        ]
        
        for nid, birth_year in valid_nids:
            is_valid, error = validate_rwanda_nid(nid, birth_year)
            if is_valid:
                print(f"✅ Valid NID accepted: {nid} (birth year: {birth_year})")
            else:
                print(f"❌ Valid NID rejected: {nid} - {error}")
                return False
        
        # Invalid NIDs
        invalid_nids = [
            ("12345678", 1998, "Too short"),
            ("1199980012345678", 2000, "Birth year mismatch"),
            ("2199980012345678", 1998, "Invalid start digit"),
        ]
        
        for nid, birth_year, reason in invalid_nids:
            is_valid, error = validate_rwanda_nid(nid, birth_year)
            if is_valid:
                print(f"❌ Invalid NID accepted: {nid} ({reason})")
                return False
            else:
                print(f"✅ Invalid NID rejected: {nid} ({reason}) - Error: {error}")
        
        return True
    except Exception as e:
        print(f"❌ Validator test failed: {e}")
        return False

def test_redis_cache() -> bool:
    """Test 6: Verify Redis cache is working."""
    print_header("Test 6: Redis Cache Connection")
    
    try:
        # Test cache set/get
        cache.set('test_key', 'test_value', 10)
        value = cache.get('test_key')
        
        if value == 'test_value':
            print("✅ Redis cache working (set/get successful)")
            cache.delete('test_key')
            return True
        else:
            print(f"❌ Redis cache failed: expected 'test_value', got '{value}'")
            return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("⚠️  Make sure Redis is running: docker-compose up -d redis")
        return False

def test_middleware() -> bool:
    """Test 7: Verify middleware is configured."""
    print_header("Test 7: Middleware Configuration")
    
    try:
        from django.conf import settings
        
        required_middleware = [
            'core.middleware.SecurityHeadersMiddleware',
            'core.middleware.AuditLoggingMiddleware',
            'core.middleware.RateLimitMetadataMiddleware',
        ]
        
        for mw in required_middleware:
            if mw in settings.MIDDLEWARE:
                print(f"✅ {mw.split('.')[-1]} configured")
            else:
                print(f"❌ {mw.split('.')[-1]} missing from MIDDLEWARE")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Middleware check failed: {e}")
        return False

def test_authentication_backends() -> bool:
    """Test 8: Verify authentication backends."""
    print_header("Test 8: Authentication Backends")
    
    try:
        from django.conf import settings
        
        required_backends = [
            'ishemalink.auth_backends.HybridAuthentication',
            'ishemalink.auth_backends.PhoneBackend',
        ]
        
        for backend in required_backends:
            if backend in settings.AUTHENTICATION_BACKENDS:
                print(f"✅ {backend.split('.')[-1]} configured")
            else:
                print(f"❌ {backend.split('.')[-1]} missing from AUTHENTICATION_BACKENDS")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Authentication backend check failed: {e}")
        return False

def test_encryption_key_exists() -> bool:
    """Test 9: Verify encryption key is set."""
    print_header("Test 9: Encryption Key Configuration")
    
    try:
        from django.conf import settings
        
        key = settings.FIELD_ENCRYPTION_KEY
        
        if not key:
            print("❌ FIELD_ENCRYPTION_KEY not set in settings")
            print("⚠️  Run: python generate_keys.py")
            return False
        
        # Try to create Fernet instance (validates key format)
        Fernet(key.encode())
        print(f"✅ Valid Fernet encryption key configured")
        print(f"   Key: {key[:20]}... (truncated)")
        
        return True
    except Exception as e:
        print(f"❌ Encryption key invalid: {e}")
        print("⚠️  Run: python generate_keys.py")
        return False

def run_all_tests() -> None:
    """Run all integration tests and print summary."""
    print("\n" + "🚀" * 30)
    print("ISHEMALINK API - FORMATIVE 2 INTEGRATION TESTS")
    print("🚀" * 30)
    
    tests = [
        ("Models Existence", test_models_exist),
        ("Field Encryption", test_encryption),
        ("User Roles (RBAC)", test_user_roles),
        ("Permission Classes", test_permissions),
        ("NID Validation", test_validators),
        ("Redis Cache", test_redis_cache),
        ("Middleware Config", test_middleware),
        ("Auth Backends", test_authentication_backends),
        ("Encryption Key", test_encryption_key_exists),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System ready for demo.")
        print("\nNext steps:")
        print("1. Create superuser: python manage.py createsuperuser")
        print("2. Start server: python manage.py runserver")
        print("3. Visit docs: http://127.0.0.1:8000/api/docs/")
    else:
        print("\n⚠️  Some tests failed. Review errors above.")
        print("Check INTEGRATION_COMPLETE.md for troubleshooting.")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    run_all_tests()
