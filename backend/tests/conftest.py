"""Test bootstrap.

Some modules (services/repositories) import the app config + DB engine at import
time, which requires these env vars. The pure-logic tests never actually open a
connection or call OpenAI, so dummy defaults are enough to import them on a host
without a real .env. Real values (in Docker) are left untouched.
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
