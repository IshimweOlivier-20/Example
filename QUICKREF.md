# IshemaLink API - Quick Reference Commands

## Development Setup
```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate encryption keys
python generate_keys.py

# 4. Setup environment
cp .env.example .env
# Edit .env with generated keys

# 5. Database setup
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# 6. Run development server
python manage.py runserver
```

## Common Management Commands
```bash
# Create superuser
python manage.py createsuperuser

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Django shell
python manage.py shell

# Clear cache
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Run tests
python manage.py test

# Collect static files (production)
python manage.py collectstatic --noinput
```

## Testing API Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/api/status/
```

### 2. Session Login
```bash
curl -X POST http://localhost:8000/api/auth/login/session/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+250788123456", "password": "yourpass"}' \
  -c cookies.txt
```

### 3. JWT Login
```bash
curl -X POST http://localhost:8000/api/auth/token/obtain/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+250788123456", "password": "yourpass"}'
```

Save the returned `access` token, then:

```bash
# Use JWT token
curl http://localhost:8000/api/auth/whoami/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Register New User
```bash
curl -X POST http://localhost:8000/api/identity/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+250788999888",
    "password": "SecurePass123",
    "full_name": "Test User",
    "user_type": "CUSTOMER"
  }'
```

### 5. Verify OTP
```bash
curl -X POST http://localhost:8000/api/identity/verify-otp/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+250788999888",
    "otp_code": "123456"
  }'
```

### 6. Submit NID for KYC
```bash
curl -X POST http://localhost:8000/api/identity/kyc/nid/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "national_id": "1199512345678901",
    "birth_year": 1995
  }'
```

### 7. Export Personal Data
```bash
curl http://localhost:8000/api/privacy/my-data/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 8. View Audit Logs
```bash
curl http://localhost:8000/api/compliance/audit-logs/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 9. Anonymize Account
```bash
curl -X POST http://localhost:8000/api/privacy/anonymize/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Database Operations

### PostgreSQL Commands
```bash
# Connect to database
psql -U ishemalink -d ishemalink_db

# List tables
\dt

# View users
SELECT id, phone, user_type, is_verified FROM users;

# View audit logs
SELECT user_phone, action, resource_type, timestamp 
FROM audit_logs 
ORDER BY timestamp DESC 
LIMIT 10;

# View encrypted NID (will show ciphertext)
SELECT id, phone, nid_number FROM users WHERE nid_number IS NOT NULL;

# Exit
\q
```

### Redis Commands
```bash
# Connect to Redis
redis-cli

# Check connection
PING

# View all keys
KEYS *

# View OTP data
KEYS *otp*

# Clear all cache
FLUSHDB

# Exit
exit
```

## Django Shell Commands

### Create Test Users
```python
from core.models import User

# Customer
customer = User.objects.create(
    phone='+250788111222',
    full_name='Test Customer',
    user_type='CUSTOMER'
)
customer.set_password('test123')
customer.save()

# Agent
agent = User.objects.create(
    phone='+250788333444',
    full_name='Sector Agent',
    user_type='AGENT',
    assigned_sector='Gasabo',
    is_verified=True
)
agent.set_password('agent123')
agent.save()

# Driver
driver = User.objects.create(
    phone='+250788555666',
    full_name='Delivery Driver',
    user_type='DRIVER',
    is_verified=True
)
driver.set_password('driver123')
driver.save()

# Government Official
gov = User.objects.create(
    phone='+250788777888',
    full_name='RURA Inspector',
    user_type='GOV_OFFICIAL',
    is_verified=True,
    is_staff=True
)
gov.set_password('rura123')
gov.save()
```

### Create Shipping Zones
```python
from core.models import ShippingZone
from decimal import Decimal

ShippingZone.objects.create(
    code='ZONE_1',
    name='Kigali',
    base_rate=Decimal('2000'),
    per_kg_rate=Decimal('500'),
    description='Kigali city deliveries'
)

ShippingZone.objects.create(
    code='ZONE_2',
    name='Provinces',
    base_rate=Decimal('3000'),
    per_kg_rate=Decimal('800'),
    description='Rwanda provinces'
)

ShippingZone.objects.create(
    code='ZONE_3',
    name='EAC Countries',
    base_rate=Decimal('15000'),
    per_kg_rate=Decimal('2000'),
    description='East African Community'
)
```

### Test Encryption
```python
from core.models import User

# Create user with encrypted NID
user = User.objects.create(
    phone='+250789000111',
    nid_number='1199512345678901',  # Will be encrypted
    full_name='Encryption Test'
)
user.set_password('test')
user.save()

# Read back (decrypted automatically)
print(f"Decrypted NID: {user.nid_number}")

# Check in database (will show ciphertext)
# psql: SELECT nid_number FROM users WHERE phone = '+250789000111';
```

### View Audit Logs
```python
from core.models import AuditLog

# Recent logs
logs = AuditLog.objects.all()[:10]
for log in logs:
    print(f"{log.timestamp} - {log.user_phone} {log.action} {log.resource_type}:{log.resource_id}")
```

## Generate Test Data

### Create Sample Shipments
```python
from domestic.models import DomesticShipment
from core.models import User
from decimal import Decimal

customer = User.objects.get(phone='+250788111222')

DomesticShipment.objects.create(
    customer=customer,
    origin='Nyabugogo, Kigali',
    destination='Kimironko, Gasabo',
    weight_kg=Decimal('5.5'),
    description='Electronics package',
    cost=Decimal('4750'),
    recipient_name='Jean Doe',
    recipient_phone='+250788999000',
    transport_type='MOTO',
    status='PENDING'
)
```

## Production Deployment

### Generate Production Keys
```bash
python generate_keys.py
# Copy output to production .env file
```

### Environment Variables (Production)
```bash
SECRET_KEY=<generated-secret-key>
FIELD_ENCRYPTION_KEY=<generated-fernet-key>
DEBUG=False
ALLOWED_HOSTS=api.ishemalink.rw,ishemalink.rw
SECURE_SSL_REDIRECT=True

DB_NAME=ishemalink_db
DB_USER=ishemalink
DB_PASSWORD=<strong-password>
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://:password@localhost:6379/0

SMS_GATEWAY_URL=https://sms.example.rw/api/send
SMS_GATEWAY_API_KEY=<actual-api-key>
```

### Run with Gunicorn
```bash
gunicorn ishemalink.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 120 \
  --access-logfile /var/log/gunicorn/access.log \
  --error-logfile /var/log/gunicorn/error.log
```

### Backup Database
```bash
# Backup
pg_dump -U ishemalink -d ishemalink_db > backup_$(date +%Y%m%d).sql

# Restore
psql -U ishemalink -d ishemalink_db < backup_20260213.sql
```

## Troubleshooting

### "No module named 'cryptography'"
```bash
pip install cryptography==41.0.7
```

### "FIELD_ENCRYPTION_KEY not set"
```bash
python generate_keys.py
# Add to .env: FIELD_ENCRYPTION_KEY=<generated-key>
```

### "Redis connection error"
```bash
# Check Redis status
redis-cli ping  # Should return PONG

# Start Redis
# Windows: redis-server
# Linux: sudo systemctl start redis
```

### "Migration conflicts"
```bash
python manage.py migrate core zero
python manage.py migrate
```

### "Decryption failed"
```
# Encryption key changed - data is unrecoverable
# Either restore original key or clear encrypted data
```

## Quick Links

- **API Docs**: http://localhost:8000/api/docs/
- **Admin Panel**: http://localhost:8000/admin/
- **Health Check**: http://localhost:8000/api/status/

## Documentation

- `README.md` - Project overview
- `SETUP.md` - Detailed setup guide
- `SECURITY.md` - Security architecture
- `IMPLEMENTATION_SUMMARY.md` - Feature checklist

---

**Last Updated**: 2026-02-13  
**Version**: 2.0 (Formative 2)
