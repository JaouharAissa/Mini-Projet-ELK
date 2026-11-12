import os


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/data/uploads")

    ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB = os.getenv("MONGO_DB", "logmonitor")
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD") or None
    INDEX_PATTERN = "logs-security-*"
    CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "60"))
