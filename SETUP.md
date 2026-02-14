# IshemaLink API - Formative 2 Setup Guide

## Overview
This guide walks through setting up the security-hardened IshemaLink API with all Formative 2 features:
- Hybrid Authentication (Session + JWT)
- Identity Verification & KYC
- Field-Level Encryption
- Audit Logging (Glass Log)
- RBAC Permissions

---

## Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis 6+
- Git

---

## Installation Steps

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd ishemalink_api
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Generate Security Keys
```bash
python generate_keys.py
```
**⚠️ IMPORTANT**: Save the generated keys securely. Copy them to `.env` file.

### 5. Configure Environment Variables
Create `.env` file from template:
```bash
cp .env.example .env
```

Edit `.env` with your generated keys:
```env
SECRET_KEY=<generated-secret-key>
FIELD_ENCRYPTION_KEY=<generated-fernet-key>
DEBUG=True

# Database
DB_NAME=ishemalink_db
DB_USER=ishemalink
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0
```

### 6. Setup PostgreSQL Database
```bash
# Login to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE ishemalink_db;
CREATE USER ishemalink WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE ishemalink_db TO ishemalink;
ALTER USER ishemalink CREATEDB;  # For running tests
\q
```

### 7. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

**Expected Output**:
```
Running migrations:
  Applying core.0001_initial... OK
  Applying core.0002_user_encryption_fields... OK
  Applying core.0003_auditlog... OK
  Applying core.0004_otpverification... OK
  Applying core.0005_shippingtariff... OK
  ...
```

### 8. Create Superuser
```bash
python manage.py createsuperuser
```
Enter phone number (e.g., `+250788123456`) and password.

### 9. Load Initial Data (Optional)
```bash
# Create shipping zones
python manage.py shell
```

```python
from core.models import ShippingZone
from decimal import Decimal

# Zone 1: Kigali
ShippingZone.objects.create(
    code='ZONE_1',
    name='Kigali',
    base_rate=Decimal('2000'),
    per_kg_rate=Decimal('500'),
    description='Kigali city deliveries'
)

# Zone 2: Provinces
ShippingZone.objects.create(
    code='ZONE_2',
    name='Provinces',
    base_rate=Decimal('3000'),
    per_kg_rate=Decimal('800'),
    description='Rwanda provinces'
)

# Zone 3: EAC
ShippingZone.objects.create(
    code='ZONE_3',
    name='EAC Countries',
    base_rate=Decimal('15000'),
    per_kg_rate=Decimal('2000'),
    description='East African Community'
)

exit()
```

### 10. Start Redis (Required for OTP cache)
```bash
# Windows (if installed via Chocolatey)
redis-server

# Linux
sudo systemctl start redis

# Mac
brew services start redis
```

### 11. Run Development Server
```bash
python manage.py runserver
```

Server starts at: `http://127.0.0.1:8000`

---

## Verification Tests

### 1. Check API Root
```bash
curl http://127.0.0.1:8000/api/
```

Expected: JSON with API endpoints

### 2. Check Health Status
```bash
curl http://127.0.0.1:8000/api/status/
```

Expected:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "v1"
}
```

### 3. Check API Documentation
Open browser: `http://127.0.0.1:8000/api/docs/`

You should see Swagger UI with all endpoints organized by tags:
- Authentication
- Identity
- Privacy
- Compliance
- Government
- Operations

### 4. Test Session Login
```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/session/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+250788123456", "password": "your-password"}' \
  -c cookies.txt
```

Expected: Session cookie saved to `cookies.txt`

### 5. Test JWT Login
```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/obtain/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+250788123456", "password": "your-password"}'
```

Expected:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### 6. Test Whoami (JWT)
```bash
curl http://127.0.0.1:8000/api/auth/whoami/ \
  -H "Authorization: Bearer <your-access-token>"
```

Expected: User profile data

### 7. Test Registration Flow
```bash
# Register new user
curl -X POST http://127.0.0.1:8000/api/identity/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+250788999888",
    "password": "TestPass123",
    "full_name": "Test User",
    "user_type": "CUSTOMER"
  }'
```

Expected: Response with `otp_code` (in development mode)

```bash
# Verify OTP
curl -X POST http://127.0.0.1:8000/api/identity/verify-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+250788999888",
    "otp_code": "123456"
  }'
```

Expected: Account activated

---

## Database Inspection (Verify Encryption)

### 1. Access Django Shell
```bash
python manage.py shell
```

### 2. Create Test User with Encrypted NID
```python
from core.models import User

# Create user with NID
user = User.objects.create(
    phone='+250788777666',
    nid_number='1199512345678901',  # Will be encrypted
    full_name='Test Encryption',
    user_type='CUSTOMER'
)
user.set_password('password123')
user.save()

# Read back (decrypted automatically)
print(f"Decrypted NID: {user.nid_number}")
```

### 3. Check Database Directly
```bash
psql -U ishemalink -d ishemalink_db
```

```sql
-- View encrypted data
SELECT id, phone, nid_number FROM users WHERE phone = '+250788777666';
```

**Expected**: `nid_number` column shows encrypted ciphertext (gibberish), NOT plain text.

### 4. Verify Audit Logs
```sql
-- View audit logs
SELECT user_phone, action, resource_type, resource_id, timestamp 
FROM audit_logs 
ORDER BY timestamp DESC 
LIMIT 10;
```

---

## Testing RBAC

### 1. Create Agent User
```python
from core.models import User

agent = User.objects.create(
    phone='+250788555444',
    full_name='Sector Agent',
    user_type='AGENT',
    assigned_sector='Gasabo',
    is_verified=True
)
agent.set_password('agent123')
agent.save()
```

### 2. Test Sector Restriction
```bash
# Login as agent
curl -X POST http://127.0.0.1:8000/api/auth/token/obtain/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+250788555444", "password": "agent123"}'

# Access sector stats (should work)
curl http://127.0.0.1:8000/api/ops/sector-stats/ \
  -H "Authorization: Bearer <agent-token>"
```

Expected: Statistics for Gasabo sector only

### 3. Create Government User
```python
gov = User.objects.create(
    phone='+250788333222',
    full_name='RURA Inspector',
    user_type='GOV_OFFICIAL',
    is_verified=True,
    is_staff=True
)
gov.set_password('rura123')
gov.save()
```

### 4. Test Government Read-Only Access
```bash
# Login as gov official
curl -X POST http://127.0.0.1:8000/api/auth/token/obtain/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+250788333222", "password": "rura123"}'

# Access government manifests (should work - read-only)
curl http://127.0.0.1:8000/api/gov/manifests/ \
  -H "Authorization: Bearer <gov-token>"
```

Expected: All shipment data (read-only view)

---

## Common Issues & Solutions

### Issue 1: "No module named 'cryptography'"
**Solution**:
```bash
pip install cryptography==41.0.7
```

### Issue 2: "FIELD_ENCRYPTION_KEY not set"
**Solution**: Run `python generate_keys.py` and add key to `.env`

### Issue 3: Migration errors
**Solution**:
```bash
# Reset migrations (WARNING: deletes data)
python manage.py migrate core zero
python manage.py migrate
```

### Issue 4: Redis connection failed
**Solution**: Check if Redis is running:
```bash
redis-cli ping
```
Expected: `PONG`

### Issue 5: "Decryption failed"
**Solution**: Encryption key changed. Either:
1. Restore original key from backup
2. Delete encrypted data and re-enter (data loss!)

---

## Production Deployment Notes

### 1. Update Settings
Edit `.env`:
```env
DEBUG=False
ALLOWED_HOSTS=api.ishemalink.rw,ishemalink.rw
SECURE_SSL_REDIRECT=True
```

### 2. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 3. Run with Gunicorn
```bash
gunicorn ishemalink.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### 4. Setup Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name api.ishemalink.rw;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 5. Setup SSL with Let's Encrypt
```bash
sudo certbot --nginx -d api.ishemalink.rw
```

---

## Next Steps

1. ✅ Review `SECURITY.md` for detailed security architecture
2. ✅ Test all endpoints using Swagger UI (`/api/docs/`)
3. ✅ Create test users for each role (CUSTOMER, AGENT, DRIVER, ADMIN, GOV_OFFICIAL)
4. ✅ Verify audit logging by checking `audit_logs` table
5. ✅ Test rate limiting by making 6 login attempts in 1 minute
6. ✅ Export user data via `/api/privacy/my-data/` endpoint
7. ✅ Test encryption by inspecting database directly

---

## Support

For technical issues:
- GitHub Issues: <your-repo-url>/issues
- Email: support@ishemalink.rw

For security vulnerabilities:
- Email: security@ishemalink.rw (do not open public issues)

---

**Document Version**: 2.0  
**Last Updated**: 2026-02-13
