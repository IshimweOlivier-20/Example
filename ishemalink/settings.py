"""
Django settings for ishemalink project.
Security-hardened configuration for Formative 2.

Compliance:
- Law N° 058/2021: Data Protection and Privacy Law
- NCSA Cybersecurity Framework
- RURA Telecommunications Regulations
"""

from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = config('SECRET_KEY', default='django-insecure-default-key-change-me')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Field-level encryption key (Fernet)
# Compliance: Law N° 058/2021 Article 22 - encryption of sensitive data
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default=None)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',  # JWT authentication
    'rest_framework_simplejwt.token_blacklist',  # JWT blacklist for logout
    'drf_spectacular',
    'django_filters',
    'corsheaders',
    
    # Local apps
    'core',
    'domestic',
    'international',
    'shipments',
    'billing',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom security middleware
    'core.middleware.SecurityHeadersMiddleware',  # HSTS, CSP, etc.
    'core.middleware.AuditLoggingMiddleware',  # Glass Log implementation
    'core.middleware.RateLimitMetadataMiddleware',  # Rate limit headers
]

ROOT_URLCONF = 'ishemalink.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ishemalink.wsgi.application'

# Database
# Use SQLite for development/testing (no Docker required)
# For production, switch back to PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# PostgreSQL configuration (commented out - uncomment for production)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': config('DB_NAME', default='ishemalink_db'),
#         'USER': config('DB_USER', default='ishemalink'),
#         'PASSWORD': config('DB_PASSWORD', default='password'),
#         'HOST': config('DB_HOST', default='localhost'),
#         'PORT': config('DB_PORT', default='5432'),
#     }
# }

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Authentication backends
# Supports both phone-based login and hybrid auth
AUTHENTICATION_BACKENDS = [
    'ishemalink.auth_backends.HybridAuthentication',  # Hybrid (Session + JWT)
    'ishemalink.auth_backends.PhoneBackend',  # Phone-based authentication
    'django.contrib.auth.backends.ModelBackend',  # Default (for admin)
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Kigali'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# REST FRAMEWORK CONFIGURATION
# ============================================================================

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.ManifestPagination',
    'PAGE_SIZE': 20,
    
    # Filters
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    
    # Hybrid Authentication Strategy
    # Priority: Session first, then JWT
    # Compliance: Supports both web dashboard and mobile app
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'ishemalink.auth_backends.HybridAuthentication',  # Custom hybrid auth
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT fallback
        'rest_framework.authentication.SessionAuthentication',  # Session fallback
    ],
    
    # Default permissions
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    
    # Throttling / Rate Limiting
    # Compliance: NCSA cybersecurity - brute force protection
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',  # Anonymous users: 100 requests per hour
        'user': '1000/hour',  # Authenticated users: 1000 requests per hour
        'login': '5/min',  # Login attempts: 5 per minute (brute force prevention)
        'otp': '3/hour',  # OTP generation: 3 per hour per phone
    },
    
    # Error handling
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    
    # Date/Time formats
    'DATETIME_FORMAT': '%Y-%m-%dT%H:%M:%S%z',
}

# ============================================================================
# JWT CONFIGURATION (Simple JWT)
# ============================================================================

SIMPLE_JWT = {
    # Token lifetimes
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),  # 1 hour
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),  # 7 days
    
    # Token rotation
    'ROTATE_REFRESH_TOKENS': True,  # Generate new refresh token on refresh
    'BLACKLIST_AFTER_ROTATION': True,  # Blacklist old refresh token
    
    # Algorithm
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    
    # Custom claims
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    
    # Additional custom claims (user_type, is_verified for mobile app logic)
    'TOKEN_OBTAIN_SERIALIZER': 'rest_framework_simplejwt.serializers.TokenObtainPairSerializer',
    
    # Token types
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    
    # Security
    'UPDATE_LAST_LOGIN': True,
}

# ============================================================================
# SPECTACULAR SETTINGS (OpenAPI Documentation)
# ============================================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'IshemaLink API',
    'DESCRIPTION': 'Logistics platform API for Rwanda - Security Hardened',
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/',
    'ENUM_ADD_EXPLICIT_BLANK_NULL_CHOICE': False,
    'DEEP_PAGINATION': 100,
}

# ============================================================================
# CACHE CONFIGURATION (Redis)
# ============================================================================

# Use local memory cache for development/testing (no Redis required)
# For production, switch back to Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'ishemalink-cache',
        'KEY_PREFIX': 'ishemalink',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Redis configuration (commented out - uncomment for production)
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': config('REDIS_URL', default='redis://localhost:6379/0'),
#         'KEY_PREFIX': 'ishemalink',
#         'TIMEOUT': 300,  # 5 minutes default
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         }
#     }
# }

# Cache TTL settings
CACHE_TTL_TARIFFS = 60 * 60 * 24 * 7  # 7 days
CACHE_TTL_OTP = 60 * 5  # 5 minutes for OTP

# ============================================================================
# SECURITY SETTINGS
# ============================================================================

# HTTPS/SSL (Production)
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session Security
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
SESSION_COOKIE_AGE = 3600 * 8  # 8 hours

# CSRF Security
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Content Security
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# ============================================================================
# CORS SETTINGS
# ============================================================================

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=Csv()
)

CORS_ALLOW_CREDENTIALS = True  # Allow cookies for session auth

# ============================================================================
# SMS & EXTERNAL SERVICES
# ============================================================================

SMS_GATEWAY_URL = config('SMS_GATEWAY_URL', default='mock://localhost')
SMS_GATEWAY_API_KEY = config('SMS_GATEWAY_API_KEY', default='')

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'security': {
            'format': '[SECURITY] {levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'async_tasks.log',
            'formatter': 'verbose',
        },
        'security_file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'formatter': 'security',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'async_tasks': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
