"""SchemeSaathi AI — Configuration classes."""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── JWT ──────────────────────────────────────────────────────
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret-change-me")
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "false").lower() == "true"
    JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "Lax")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "900"))
    )
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "2592000"))
    )
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_IN_COOKIES = True

    # ── Rate Limiting ────────────────────────────────────────────
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "60/minute")
    RATELIMIT_STORAGE_URI = "memory://"

    # ── Gemini API ───────────────────────────────────────────────
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_EMBEDDING_MODEL = os.getenv(
        "GEMINI_EMBEDDING_MODEL", "models/text-embedding-004"
    )

    # ── FAISS ────────────────────────────────────────────────────
    FAISS_INDEX_PATH = os.getenv(
        "FAISS_INDEX_PATH", "../data/vector_index/faiss.idx"
    )
    FAISS_METADATA_PATH = os.getenv(
        "FAISS_METADATA_PATH", "../data/vector_index/metadata.json"
    )

    # ── RAG Pipeline ─────────────────────────────────────────────
    RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
    RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "80"))
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "6"))


class DevelopmentConfig(Config):
    """Local development with SQLite default (or MySQL via DATABASE_URL)."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///schemesaathi_dev.db",
    )


class TestingConfig(Config):
    """In-memory SQLite for fast tests (no MySQL required)."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_CSRF_PROTECT = False
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production — requires DATABASE_URL in environment."""

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    JWT_COOKIE_SECURE = True


config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
