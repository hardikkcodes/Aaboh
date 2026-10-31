"""Django settings for the Aaboh Platform.

Configuration is environment-driven. Development defaults are deliberately
usable without Docker or external credentials; production must set explicit
secrets and ``DJANGO_DEBUG=false``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key-do-not-use-in-production")
DEBUG = env_bool("DJANGO_DEBUG", False)
if not DEBUG and (SECRET_KEY.startswith("dev-only") or len(SECRET_KEY) < 50):
    raise ImproperlyConfigured(
        "Set DJANGO_SECRET_KEY to a random value of at least 50 characters, "
        "or set DJANGO_DEBUG=true for local development."
    )
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
# Trusted reverse proxies in front of Django. Zero ignores X-Forwarded-For, which
# clients can forge to escape rate limits.
NUM_PROXIES = int(os.getenv("DJANGO_NUM_PROXIES", "0"))

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "apps.core",
    "apps.accounts",
    "apps.locations",
    "apps.weather",
    "apps.alerts",
    "apps.air_quality",
    "apps.environment",
    "apps.heat",
    "apps.incidents",
    "apps.rainfall",
    "apps.climate",
    "apps.intelligence",
    "apps.notifications",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if os.getenv("DB_ENGINE", "sqlite").lower() == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "civic_climate"),
            "USER": os.getenv("POSTGRES_USER", "civic"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {"timeout": 20},
        }
    }

# Rate limits live in the cache, so multiple Gunicorn workers need a shared one.
CACHE_DIR = os.getenv("DJANGO_CACHE_DIR", "")
if CACHE_DIR:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": CACHE_DIR,
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("INCIDENT_IMAGE_MAX_BYTES", "5242880")) * 5 + 262144
FILE_UPLOAD_MAX_MEMORY_SIZE = 2_621_440
DATA_UPLOAD_MAX_NUMBER_FILES = 4

# Account emails print to the console until a mail host is configured.
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_TIMEOUT = 10
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@localhost")
# Turn on once email delivery works, so new accounts must confirm before reporting.
ACCOUNT_REQUIRE_VERIFIED_EMAIL = env_bool("ACCOUNT_REQUIRE_VERIFIED_EMAIL", False)

CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    "NUM_PROXIES": NUM_PROXIES,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
        "user": "600/min",
        "auth": "10/min",
        "incident_create": "12/hour",
        "incident_confirm": "60/hour",
    },
}

if not DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = ["rest_framework.renderers.JSONRenderer"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_REDIRECT_EXEMPT = [r"^api/v1/health/"]
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "2592000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
    SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
    if NUM_PROXIES:
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SPECTACULAR_SETTINGS = {
    "TITLE": "Aaboh API",
    "DESCRIPTION": (
        "Public environmental intelligence for Kolkata. Responses separate observation, "
        "forecast, prediction, official warning and community report; source and freshness "
        "metadata is returned with environmental records."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "IncidentStatusEnum": "apps.incidents.models.IncidentStatus.choices",
    },
    "TAGS": [
        {"name": "system", "description": "Health, configuration and data availability"},
        {"name": "locations", "description": "Areas, neighbourhoods and analytical grid"},
        {"name": "weather", "description": "Current conditions and forecasts"},
        {"name": "alerts", "description": "Official weather warnings"},
        {"name": "air-quality", "description": "Monitoring-station measurements"},
        {"name": "environment", "description": "Satellite-derived environmental observations"},
        {"name": "heat", "description": "Urban heat observations, hotspots and model predictions"},
        {"name": "rainfall", "description": "Rainfall forecast and history"},
        {"name": "climate", "description": "Long-term climate metrics and trends"},
        {"name": "incidents", "description": "Community environmental reports"},
        {"name": "insights", "description": "Transparent evidence-backed local guidance"},
    ],
}

APP_CONFIG = {
    "name": os.getenv("APP_NAME", "Aaboh"),
    "short_name": os.getenv("APP_SHORT_NAME", "Aaboh"),
    "tagline": os.getenv("APP_TAGLINE", "Hyperlocal environmental intelligence for Kolkata"),
    "support_email": os.getenv("APP_SUPPORT_EMAIL", ""),
    "default_city": "Kolkata",
    "timezone": "Asia/Kolkata",
    "frontend_url": os.getenv("FRONTEND_URL", "http://localhost:5173"),
    "branding_configurable": True,
}

OPEN_METEO_ENABLED = env_bool("OPEN_METEO_ENABLED", True)
OPEN_METEO_TIMEOUT = int(os.getenv("OPEN_METEO_TIMEOUT_SECONDS", "30"))
IMD_API_KEY = os.getenv("IMD_API_KEY", "")
IMD_API_KEY_HEADER = os.getenv("IMD_API_KEY_HEADER", "X-API-Key")
IMD_BASE_URL = os.getenv("IMD_BASE_URL", "https://api.imd.gov.in/api/v1")
CPCB_API_KEY = os.getenv("CPCB_API_KEY", "")
CPCB_RESOURCE_ID = os.getenv("CPCB_RESOURCE_ID", "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69")
CPCB_BASE_URL = os.getenv("CPCB_BASE_URL", "https://api.data.gov.in/resource")
CPCB_TIMEOUT = int(os.getenv("CPCB_TIMEOUT_SECONDS", "60"))
# Cities the CPCB resource is queried for by default. The national feed also
# works (--all-cities) but Kolkata/Howrah keep the stored footprint local.
CPCB_CITIES = env_list("CPCB_CITIES", "Kolkata,Howrah")
SACHET_BASE_URL = os.getenv("SACHET_BASE_URL", "https://sachet.ndma.gov.in")
SACHET_TIMEOUT = int(os.getenv("SACHET_TIMEOUT_SECONDS", "45"))
# Terms used to decide whether a national SACHET alert covers Kolkata. The feed
# publishes area text only, so this is a word match, not a geospatial query.
SACHET_SCOPE_TERMS = env_list(
    "SACHET_SCOPE_TERMS", "kolkata,howrah,haora,hooghly,24 parganas,west bengal"
)
ALERT_STATE_TERMS = env_list("ALERT_STATE_TERMS", "west bengal,gangetic bengal")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GEE_PROJECT_ID = os.getenv("GEE_PROJECT_ID", "")
GEE_SERVICE_ACCOUNT_EMAIL = os.getenv("GEE_SERVICE_ACCOUNT_EMAIL", "")
GEE_SERVICE_ACCOUNT_KEY_FILE = os.getenv("GEE_SERVICE_ACCOUNT_KEY_FILE", "")
INCIDENT_IMAGE_MAX_BYTES = int(os.getenv("INCIDENT_IMAGE_MAX_BYTES", "5242880"))
INCIDENT_IMAGE_MAX_COUNT = int(os.getenv("INCIDENT_IMAGE_MAX_COUNT", "4"))
PUBLIC_SITE_URL = os.getenv("PUBLIC_SITE_URL", "http://localhost:8000")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "apps.core.logging.JsonFormatter"},
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": os.getenv("DJANGO_LOG_FORMAT", "plain"),
        }
    },
    "root": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "apps": {"handlers": ["console"], "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"), "propagate": False},
        "data_pipelines": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
