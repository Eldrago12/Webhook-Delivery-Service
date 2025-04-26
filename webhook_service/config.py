import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Config:
    # Database Configuration
    # Defaulting to service names used in docker-compose.yml for local dev
    POSTGRES_USER = os.environ.get("POSTGRES_USER", "user")
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")
    POSTGRES_DB = os.environ.get("POSTGRES_DB", "webhook_db")
    POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "db")
    POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = True
    # RabbitMQ Broker Configuration
    RABBITMQ_DEFAULT_USER = os.environ.get("RABBITMQ_DEFAULT_USER", "guest")
    RABBITMQ_DEFAULT_PASS = os.environ.get("RABBITMQ_DEFAULT_PASS", "guest")
    RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "rabbitmq")
    RABBITMQ_PORT = os.environ.get("RABBITMQ_PORT", "5672")
    CELERY_BROKER_URL = os.environ.get(
        "CELERY_BROKER_URL",
        f"amqp://{RABBITMQ_DEFAULT_USER}:{RABBITMQ_DEFAULT_PASS}@{RABBITMQ_HOST}:{RABBITMQ_PORT}//" # The last / is for the default vhost
    )

    # Redis Configuration (for Celery backend and Cache)
    REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
    REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
    CELERY_RESULT_BACKEND = os.environ.get(
        "CELERY_RESULT_BACKEND",
        f"redis://{REDIS_HOST}:{REDIS_PORT}/0" # DB 0 for Celery results
    )
    REDIS_CACHE_URL = os.environ.get(
        "REDIS_CACHE_URL",
        f"redis://{REDIS_HOST}:{REDIS_PORT}/1" # DB 1 for Cache
    )

    # Celery Configuration
    CELERY_TASK_IGNORE_RESULT = False
    CELERY_TASK_TRACK_STARTED = True
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True

    # Webhook Delivery Settings
    DELIVERY_TIMEOUT_SECONDS = int(os.environ.get("DELIVERY_TIMEOUT_SECONDS", "10"))
    MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "5"))
    # Exponential Backoff: base * (factor ^ (attempts - 1))
    RETRY_BASE_DELAY_SECONDS = int(os.environ.get("RETRY_BASE_DELAY_SECONDS", "10")) # First retry after 10s
    RETRY_FACTOR = int(os.environ.get("RETRY_FACTOR", "3")) # Delays: 10s, 30s, 90s, 270s, 810s (~13.5m)
    MAX_RETRY_DELAY_SECONDS = int(os.environ.get("MAX_RETRY_DELAY_SECONDS", "900")) # Cap at 15 minutes

    # Log Retention Settings
    LOG_RETENTION_HOURS = int(os.environ.get("LOG_RETENTION_HOURS", "72")) # 72 hours

    # Caching Settings
    CACHE_EXPIRY_SECONDS = int(os.environ.get("CACHE_EXPIRY_SECONDS", "3600")) # Cache subscriptions for 1 hour

    # Bonus Points Settings (Optional)
    WEBHOOK_SECRET_HEADER = os.environ.get("WEBHOOK_SECRET_HEADER", "X-Hub-Signature-256")
    WEBHOOK_EVENT_TYPE_HEADER = os.environ.get("WEBHOOK_EVENT_TYPE_HEADER", "X-Event-Type")
    # Secret key used for signing/verification if not stored per-subscription
    # Or used as a fallback if subscription secret is not set
    # GLOBAL_WEBHOOK_SECRET = os.environ.get("GLOBAL_WEBHOOK_SECRET", "your_global_fallback_secret")

    # Flask Settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "super-secret-dev-key") # Required for Flask sessions/security
