"""Django settings for the Civic Climate Intelligence Platform.

Configuration is environment-driven. Development defaults are deliberately
usable without Docker or external credentials; production must set explicit
secrets and ``DJANGO_DEBUG=false``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

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
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

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
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
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
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
        "user": "600/min",
        "auth": "10/min",
        "incident_create": "12/hour",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Civic Climate Intelligence API",
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
    "name": os.getenv("APP_NAME", "Civic Climate"),
    "short_name": os.getenv("APP_SHORT_NAME", "CivicClimate"),
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
