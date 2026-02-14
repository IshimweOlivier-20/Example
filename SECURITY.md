# IshemaLink API - Security Implementation (Formative 2)

## Overview
This document outlines the security architecture and compliance implementation for the IshemaLink logistics platform, in accordance with:
- **Law N° 058/2021**: Rwanda Data Protection and Privacy Law
- **NCSA**: National Cyber Security Authority Guidelines  
- **RURA**: Rwanda Utilities Regulatory Authority Requirements

---

## 1. Hybrid Authentication Strategy

### Implementation
- **Dual Authentication**: Session-based (web dashboard) + JWT (mobile app)
- **Authentication Class**: `ishemalink.auth_backends.HybridAuthentication`
- **Priority Order**: Session → JWT → Fallback

### Endpoints
| Endpoint | Method | Description | Auth Type |
|----------|--------|-------------|-----------|
| `/api/auth/login/session/` | POST | Web dashboard login | Session |
| `/api/auth/token/obtain/` | POST | Mobile JWT login | JWT |
| `/api/auth/token/refresh/` | POST | Refresh JWT token | JWT |
| `/api/auth/logout/` | POST | Universal logout | Both |
| `/api/auth/whoami/` | GET | Current user info | Both |

### JWT Configuration
```python
ACCESS_TOKEN_LIFETIME = 60 minutes
REFRESH_TOKEN_LIFETIME = 7 days
ROTATE_REFRESH_TOKENS = True (security best practice)
BLACKLIST_AFTER_ROTATION = True (logout support)
```

### Rate Limiting
**Brute Force Prevention** (NCSA Compliance):
- Login attempts: **5 per minute** per IP
- OTP requests: **3 per hour** per phone
- Anonymous API: **100 per hour**
- Authenticated API: **1000 per hour**

**Implementation**: DRF Throttle Classes + Custom `LoginRateThrottle`

---

## 2. Identity & KYC Verification

### Rwanda NID Validation
**Format**: 16 digits starting with '1'
- Digits 1-4: Birth year (1900-2010)
- Digit 5: Province code (1-7)
- Digit 16: Luhn checksum

**Cross-Validation**: Birth year in NID must match user-provided birth year

**Implementation**: `core/validators.py::validate_rwanda_nid()`

### OTP Simulation
**Purpose**: Phone verification for account activation
- **Storage**: Django Cache (Redis)
- **Expiry**: 5 minutes
- **Max Attempts**: 3
- **Code Format**: 6-digit numeric

**Flow**:
1. User registers → OTP generated and cached
2. OTP sent via SMS (mocked in dev, real in prod)
3. User submits OTP → Validated against cache
4. Success → Account activated (`is_verified = True`)

### Verification Status Flags
| Field | Type | Purpose |
|-------|------|---------|
| `is_verified` | Boolean | KYC completion status |
| `verification_date` | DateTime | When KYC was completed |
| `nid_number` | EncryptedCharField | Rwanda National ID (encrypted) |
| `birth_year` | Integer | For NID cross-validation |

---

## 3. Data Privacy & Encryption

### Field-Level Encryption (Fernet)
**Compliance**: Law N° 058/2021 Article 22 - Encryption of sensitive personal data

**Encrypted Fields**:
- `nid_number`: Rwanda National ID
- `tax_id`: Tax Identification Number

**Implementation**: Custom Django field types in `core/encryption.py`
```python
from core.encryption import EncryptedCharField

nid_number = EncryptedCharField(max_length=500, blank=True)
```

**Key Management**:
- Encryption key stored in environment variable: `FIELD_ENCRYPTION_KEY`
- Generated once using: `Fernet.generate_key()`
- **⚠️ WARNING**: Never commit keys to Git. Key loss = data loss.

### "Glass Log" - Audit Trail
**Compliance**: Law N° 058/2021 Article 29 - Right to access information

**What is Logged**:
- **WHO**: User phone, user type, IP address
- **WHAT**: Resource type, resource ID, endpoint
- **WHEN**: Timestamp (Africa/Kigali timezone)
- **HOW**: HTTP method, response status

**Triggers**: All GET requests to sensitive endpoints (shipments, user profiles, billing)

**Model**: `core.models.AuditLog`

**Middleware**: `core.middleware.AuditLoggingMiddleware`

**Immutability**: Audit logs cannot be deleted (enforced in Django Admin)

### Right to be Forgotten
**Compliance**: Law N° 058/2021 Article 30 - Right to erasure

**Endpoint**: `POST /api/privacy/anonymize/`

**Implementation**:
```python
def anonymize(self):
    self.full_name = "REDACTED"
    self.phone = f"+250700000{self.id:04d}"
    self.nid_number = None
    self.tax_id = None
    self.is_active = False
```

**Note**: Shipment history retained for 7 years (legal compliance).

### Data Portability
**Endpoint**: `GET /api/privacy/my-data/`

**Returns**: JSON export of all user data:
- User profile
- Sensitive data (decrypted)
- Shipment history
- Audit log (last 100 entries)

---

## 4. Role-Based Access Control (RBAC)

### User Roles
| Role | Code | Access Level |
|------|------|--------------|
| Customer | `CUSTOMER` | Own shipments only |
| Agent | `AGENT` | Assigned sector shipments |
| Driver | `DRIVER` | Assigned deliveries (no pricing) |
| Admin | `ADMIN` | Full access |
| Gov Official | `GOV_OFFICIAL` | Read-only global access |

### Permission Classes
**File**: `core/permissions.py`

#### 1. `IsSectorAgent`
- **Purpose**: Restrict agents to their assigned 416 sector
- **Logic**: Match `assigned_sector` with shipment origin/destination
- **Object-Level**: `has_object_permission()` checks each shipment

#### 2. `IsGovOfficial`
- **Purpose**: RURA/RRA/NCSA read-only access
- **Logic**: Allow all GET requests, deny POST/PUT/DELETE
- **Compliance**: Law N° 058/2021 Article 50 - Regulatory access

#### 3. `IsDriver`
- **Purpose**: Drivers see delivery info, NOT pricing
- **Logic**: Filter serializer fields based on `user_type`
- **Business Rule**: Driver only needs "where", not "how much"

#### 4. `IsVerified`
- **Purpose**: Require KYC completion for sensitive actions
- **Logic**: Check `user.is_verified == True`
- **Use Case**: Creating shipments, viewing financial data

### QuerySet Filtering
```python
def get_queryset(self):
    if self.request.user.user_type == 'AGENT':
        sector = self.request.user.assigned_sector
        return Shipment.objects.filter(
            Q(origin__icontains=sector) | Q(destination__icontains=sector)
        )
    return Shipment.objects.all()
```

---

## 5. Security Middleware

### 1. `SecurityHeadersMiddleware`
**OWASP Best Practices**:
- `Strict-Transport-Security`: Force HTTPS for 1 year
- `X-Content-Type-Options: nosniff`: Prevent MIME sniffing
- `X-Frame-Options: DENY`: Prevent clickjacking
- `Content-Security-Policy`: Restrict resource loading

### 2. `AuditLoggingMiddleware`
**Glass Log Implementation**: Intercepts all requests, logs sensitive data access

### 3. `RateLimitMetadataMiddleware`
**Headers Added**:
- `X-RateLimit-Limit`: Max requests allowed
- `X-RateLimit-Remaining`: Requests left in window
- `X-RateLimit-Reset`: When limit resets

---

## 6. OpenAPI Documentation

### Security Schemes
1. **BearerAuth** (JWT):
   ```yaml
   type: http
   scheme: bearer
   bearerFormat: JWT
   description: Mobile authentication
   ```

2. **CookieAuth** (Session):
   ```yaml
   type: apiKey
   in: cookie
   name: sessionid
   description: Web dashboard authentication
   ```

### Error Responses
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions (wrong role)
- **429 Too Many Requests**: Rate limit exceeded

### Tag Organization
- `Authentication`: Login, logout, token management
- `Identity`: KYC, OTP, verification
- `Privacy`: Data export, anonymization, consent
- `Compliance`: Audit logs, government views
- `Operations`: Sector statistics (agents)

---

## 7. Threat Model & Mitigations

### Threat 1: Insider Threat - Rogue Agent
**Risk**: Agent accessing shipments outside their sector

**Mitigation**:
- `IsSectorAgent` permission class
- QuerySet filtering by `assigned_sector`
- Audit logging of all data access
- Regular audit review by admins

### Threat 2: Brute Force Attack
**Risk**: Automated password guessing

**Mitigation**:
- Rate limiting: 5 login attempts per minute
- Account lockout after 10 failed attempts (future feature)
- Password complexity requirements (min 8 chars, no common passwords)
- CAPTCHA integration (future feature)

### Threat 3: Data Breach - Stolen Database
**Risk**: Attacker gains access to database dump

**Mitigation**:
- Field-level encryption (Fernet) for NID and TIN
- Passwords hashed with PBKDF2 (Django default)
- Encryption keys stored separately (environment variables)
- Database access restricted to localhost only

---

## 8. Deployment Checklist

### Before Production:
- [ ] Generate strong `SECRET_KEY` (256-bit random)
- [ ] Generate `FIELD_ENCRYPTION_KEY` using Fernet
- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS` with actual domains
- [ ] Enable SSL/HTTPS (`SECURE_SSL_REDIRECT = True`)
- [ ] Use real SMS gateway API (replace mock)
- [ ] Set up log rotation for audit logs
- [ ] Configure firewall to allow only necessary ports
- [ ] Remove OTP codes from API responses (line 357 in views_auth.py)
- [ ] Set up automated database backups
- [ ] Configure Redis password authentication

### Environment Variables (Production):
```bash
SECRET_KEY=<256-bit-random-key>
FIELD_ENCRYPTION_KEY=<fernet-key>
DEBUG=False
ALLOWED_HOSTS=api.ishemalink.rw,ishemalink.rw
SECURE_SSL_REDIRECT=True
REDIS_URL=redis://:password@localhost:6379/0
SMS_GATEWAY_URL=https://sms.example.rw/api/send
SMS_GATEWAY_API_KEY=<actual-api-key>
```

---

## 9. Testing Scenarios

### Authentication Flow:
1. **Session Login**:
   ```bash
   POST /api/auth/login/session/
   {"phone": "+250788123456", "password": "SecurePass123"}
   ```
   → Returns session cookie

2. **JWT Login**:
   ```bash
   POST /api/auth/token/obtain/
   {"phone": "+250788123456", "password": "SecurePass123"}
   ```
   → Returns access + refresh tokens

3. **Rate Limit Test**:
   - Attempt 6 logins in 1 minute → 6th request returns 429

### KYC Flow:
1. Register: `POST /api/identity/register/`
2. Verify OTP: `POST /api/identity/verify-otp/`
3. Submit NID: `POST /api/identity/kyc/nid/`
4. Check status: `GET /api/identity/status/`

### Privacy Flow:
1. Export data: `GET /api/privacy/my-data/`
2. Anonymize: `POST /api/privacy/anonymize/`
3. Verify audit log: `GET /api/compliance/audit-logs/`

---

## 10. Security Decision Rationale

### Why 5 login attempts per minute?
- Balance security vs. usability
- Prevents automated brute force (1000s of attempts)
- Allows legitimate users with typos
- Industry standard (OWASP recommendation)

### Why 5-minute OTP expiry?
- SMS delivery delays in rural Rwanda (2-3 min avg)
- Short enough to prevent replay attacks
- Aligned with Rwanda telecom infrastructure

### Why JWT + Session hybrid?
- **Mobile users**: Need persistent auth (JWT) for poor network areas
- **Web agents**: Session is simpler, auto-logout on browser close
- **Flexibility**: Different use cases, different needs

### Why encrypt NID but not phone?
- **Phone**: Used for login (must be searchable)
- **NID**: Pure PII, never used in queries (can be encrypted)
- **Tax ID**: High-value target, encrypted

---

## Contact & Support
For security issues, contact: security@ishemalink.rw  
For compliance queries, contact: compliance@ishemalink.rw

---

**Document Version**: 2.0  
**Last Updated**: 2026-02-13  
**Compliance Officer**: IshemaLink Security Team
