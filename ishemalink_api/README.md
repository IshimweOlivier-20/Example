# IshemaLink API

[![Django](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.14-red.svg)](https://www.django-rest-framework.org/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)

## Overview

IshemaLink is a logistics platform API designed for Rwanda's courier market. It digitizes shipment management, connecting rural farmers to urban markets and facilitating cross-border EAC trade.

### Key Features

- **Dual Shipment Types**: Separate handling for domestic (Moto/Bus) and international (EAC) shipments
- **Rwanda KYC Compliance**: Validates Rwanda phone numbers (+250 format) and National IDs (16-digit)
- **Async Notifications**: Non-blocking SMS notifications with simulated gateway latency
- **Intelligent Caching**: Zone-based tariff caching with 7-day TTL
- **Mobile-Optimized**: Cursor pagination and minimal payloads for low-bandwidth users
- **Comprehensive Tracking**: Real-time status updates with full history logs

## Project Architecture

### App Structure

```
ishemalink_api/
├── core/                  # Shared models, validators, permissions
│   ├── models.py         # User, Location, ShippingZone, BaseShipment
│   ├── validators.py     # Rwanda phone/NID/TIN/passport validation
│   ├── pricing.py        # Tariff calculation and caching logic
│   └── views.py          # Auth endpoints
├── domestic/             # Local Rwanda deliveries
│   ├── models.py        # DomesticShipment, ShipmentLog
│   └── views.py         # CRUD + async tracking
├── international/        # Cross-border EAC shipments
│   ├── models.py        # InternationalShipment, CustomsDocument
│   └── views.py         # Extended validation + customs
└── ishemalink/          # Django project settings
    ├── settings.py
    └── urls.py
```

### Design Decisions

**Why Separate Domestic/International Apps?**
- Different validation rules (NID vs Passport/TIN)
- Distinct workflows (customs clearance for international)
- Separate status choices (AT_CUSTOMS, CLEARED_CUSTOMS)
- Avoids if/else spaghetti code in single app
- Easier to extend (e.g., add air freight as new app)

**Why Custom User Model?**
- Rwanda users authenticate with phone numbers, not email
- Stores NID for KYC compliance
- Role-based access (CUSTOMER, AGENT, ADMIN)
- Agent-specific field: `assigned_sector`

**Why Cursor Pagination?**
- Mobile agents scroll infinitely (Instagram-like UX)
- Constant O(1) performance vs O(n) for page numbers
- No duplicate results when new records added
- Better for rural agents on unstable networks

## Setup Instructions

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker (optional)

### 1. Clone Repository

```bash
git clone <repository-url>
cd ishemalink_api
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:

```
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgresql://ishemalink:password@localhost:5432/ishemalink_db
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 5. Database Setup

```bash
# Create database
createdb ishemalink_db

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser --username +250788000000
```

### 6. Seed Initial Data

```bash
python manage.py shell
```

```python
from core.models import ShippingZone
from decimal import Decimal

# Create shipping zones
ShippingZone.objects.create(
    code='ZONE_1',
    name='Kigali',
    base_rate=Decimal('1500'),
    per_kg_rate=Decimal('200'),
    description='Kigali city area'
)

ShippingZone.objects.create(
    code='ZONE_2',
    name='Provinces',
    base_rate=Decimal('3000'),
    per_kg_rate=Decimal('300'),
    description='Other Rwanda provinces'
)

ShippingZone.objects.create(
    code='ZONE_3',
    name='EAC Countries',
    base_rate=Decimal('10000'),
    per_kg_rate=Decimal('500'),
    description='Uganda, Kenya, DRC, Tanzania, Burundi'
)
```

### 7. Run Development Server

```bash
python manage.py runserver
```

Server runs at: `http://localhost:8000`

API documentation: `http://localhost:8000/api/docs/`

### Docker Setup (Alternative)

```bash
docker-compose up --build
```

## API Endpoints

### Health & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/` | API root with version info |
| GET | `/api/status/` | Health check + DB connectivity |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register customer/agent |
| POST | `/api/auth/verify-nid/` | Validate Rwanda NID |
| GET | `/api/users/me/` | Get current user profile |
| POST | `/api/users/agents/onboard/` | Agent onboarding (requires approval) |

### Domestic Shipments

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/domestic/shipments/` | List shipments (paginated) |
| POST | `/api/domestic/shipments/` | Create domestic shipment |
| GET | `/api/domestic/shipments/{id}/` | Get shipment details |
| POST | `/api/shipments/{id}/update-status/` | Async status update |
| POST | `/api/shipments/batch-update/` | Bulk async updates |
| GET | `/api/shipments/{id}/tracking/` | Full tracking history |

### International Shipments

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/international/shipments/` | List international shipments |
| POST | `/api/international/shipments/` | Create with customs docs |
| GET | `/api/international/shipments/{id}/` | Get details |
| POST | `/api/international/customs-documents/` | Add customs document |

### Pricing & Caching

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/pricing/tariffs/` | Get cached tariffs |
| POST | `/api/pricing/calculate/` | Calculate shipping cost |
| POST | `/api/pricing/admin/cache/clear-tariffs/` | Clear cache (admin) |

## Async Task Processing

This project uses Django's native async views (Django 4.2+) for non-blocking I/O operations.

### How It Works

1. **Status Update**: When a shipment status changes, the API responds immediately
2. **Background Notification**: SMS notification is sent asynchronously via `asyncio.create_task()`
3. **Mock Gateway**: Simulates 2-second API latency for realistic testing

### Running Async Workers

Django's development server automatically uses ASGI for async support:

```bash
python manage.py runserver  # Uses Daphne/Uvicorn internally
```

### Monitoring Async Tasks

Logs are written to `logs/async_tasks.log`:

```bash
tail -f logs/async_tasks.log
```

### Testing Async Behavior

```bash
# Test single async update
curl -X POST http://localhost:8000/api/shipments/1/update-status/ \
  -H "Content-Type: application/json" \
  -d '{"status": "IN_TRANSIT", "location": "Nyabugogo"}'

# Test bulk async updates
curl -X POST http://localhost:8000/api/shipments/batch-update/ \
  -H "Content-Type: application/json" \
  -d '{
    "tracking_numbers": ["RW-D-12345678", "RW-D-87654321"],
    "status": "DELIVERED",
    "location": "Recipient address"
  }'
```

## Caching Strategy

### What's Cached?

- Shipping tariffs (Zone 1, 2, 3)
- Zone definitions and pricing rules

### Cache Configuration

- **Backend**: Redis (or LocalMemory for dev)
- **TTL**: 7 days (604,800 seconds)
- **Key Pattern**: `ishemalink:tariff:zone:ZONE_1:v1`

### Why 7 Days?

- Tariffs change monthly (business requirement)
- Balance between freshness and performance
- Versioned keys (`v1`) allow instant invalidation

### Cache Headers

Responses include cache metadata:

```
X-Cache-Hit: TRUE
Cache-Control: public, max-age=3600
```

### Manual Cache Invalidation

Admin endpoint (requires staff permissions):

```bash
curl -X POST http://localhost:8000/api/pricing/admin/cache/clear-tariffs/ \
  -H "Authorization: Bearer <admin-token>"
```

## Rwanda-Specific Validations

### Phone Number Format

**Valid**: `+250 788 123 456` (MTN), `+250 722 456 789` (Airtel)

**Regex**: `^\+2507[2378]\d{7}$`

**Edge Cases**:
- Strips spaces/dashes before validation
- Rejects numbers without +250 prefix
- Network codes: 78X (MTN), 72X/73X (Airtel)

### National ID (NID) Format

**Structure**: `1 YYYY 7 XXXXXXX XXXXX C`

- Position 0: Always `1`
- Positions 1-4: Birth year (1900-2010)
- Position 5: Province code (1-7)
- Positions 6-15: Registration + sequence
- Position 15: Luhn checksum

**Validation Steps**:
1. Check 16 digits
2. Verify starts with `1`
3. Validate birth year range
4. Verify Luhn algorithm checksum

**Luhn Algorithm Implementation**:
```python
# Double every second digit from right
# If result > 9, subtract 9
# Sum all digits
# Valid if sum % 10 == 0
```

### TIN (Tax ID)

- 9 numeric digits
- Required for international shipments

### Passport

- 6-9 alphanumeric characters
- Required for international shipments

## Testing

### Run All Tests

```bash
python manage.py test
```

### Run Specific App Tests

```bash
python manage.py test core
python manage.py test domestic
python manage.py test international
```

### Test Coverage

```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

### Unit Test Examples

**Phone Validation**:
```python
from core.validators import validate_rwanda_phone

def test_valid_mtn_number():
    is_valid, error = validate_rwanda_phone('+250788123456')
    assert is_valid == True
    assert error is None
```

**NID Validation**:
```python
from core.validators import validate_rwanda_nid

def test_nid_wrong_prefix():
    is_valid, error = validate_rwanda_nid('2199870123456789')
    assert is_valid == False
    assert 'start with 1' in error
```

## API Documentation

Interactive OpenAPI documentation available at:

**Swagger UI**: `http://localhost:8000/api/docs/`

**Schema JSON**: `http://localhost:8000/api/schema/`

## Postman Collection

Import `IshemaLink_Collection.json` into Postman.

### Collection Structure

```
IshemaLink API/
├── 1. Health & Auth
│   ├── GET /api/
│   ├── GET /api/status/
│   ├── POST /api/auth/register/
│   └── POST /api/auth/verify-nid/
├── 2. Domestic Shipments
│   ├── POST /api/domestic/shipments/
│   ├── GET /api/domestic/shipments/?status=IN_TRANSIT
│   └── POST /api/shipments/{id}/update-status/
├── 3. International Shipments
│   ├── POST /api/international/shipments/
│   └── POST /api/international/customs-documents/
├── 4. Async Tracking
│   ├── POST /api/shipments/batch-update/
│   └── GET /api/shipments/{id}/tracking/
└── 5. Pricing & Caching
    ├── GET /api/pricing/tariffs/
    ├── POST /api/pricing/calculate/
    └── POST /api/pricing/admin/cache/clear-tariffs/
```

### Environment Variables

Set in Postman:
- `base_url`: `http://localhost:8000`
- `auth_token`: `<your-auth-token>`

## Reflection: Domestic vs International Logic

### Regulatory Differences

**Domestic shipments** operate within Rwanda's borders and only require local KYC compliance:
- Rwanda phone number (+250 format)
- National ID (16-digit format with Luhn checksum)
- Simple recipient contact info

**International shipments** cross EAC borders and require extensive customs documentation:
- Passport validation (alphanumeric, 6-9 chars)
- TIN (Tax ID, 9 digits)
- Commercial invoices
- Certificates of origin
- Customs declarations with estimated value

### Architectural Separation

Instead of using a single `Shipment` model with nullable fields, I chose separate models:

**Benefits**:
1. **Type Safety**: No "ghost fields" (domestic never has `passport` field)
2. **Cleaner Serializers**: Each has only relevant fields
3. **Performance**: Separate tables = optimized indexes
4. **Scalability**: Easy to add air freight without touching existing code

### Validation Strategy

Validators are separated into distinct functions rather than if/else chains:
- `validate_rwanda_phone()` - Domestic only
- `validate_rwanda_nid()` - Domestic only
- `validate_tin()` - International only
- `validate_passport()` - International only

This makes unit testing easier and code more maintainable.

### Status Flow Differences

**Domestic**: `PENDING → PICKED_UP → IN_TRANSIT → DELIVERED`

**International**: `PENDING → PICKED_UP → IN_TRANSIT → AT_CUSTOMS → CLEARED_CUSTOMS → DELIVERED`

The extended statuses for international shipments justify separate models.

### User Experience Impact

- **Domestic Form**: 3 required fields (origin, destination, weight)
- **International Form**: 10+ fields (customs docs, TIN, passport, etc.)

Different API endpoints reflect this complexity, making mobile forms simpler for domestic users.

## License

MIT License

## Contributors

Developed for ALU Backend Engineering Course - Formative 1 (February 2026)

---

**Note**: This project uses mock SMS gateway for development. Configure real gateway URL in `.env` for production use.
