import os
from pathlib import Path

DB_PATH = Path("test_app.db")
DB_URL = "sqlite:///./test_app.db"
ADMIN_EMAIL = "integration@example.com"
ADMIN_PASSWORD = "Integration123!"

os.environ.setdefault("DATABASE_URL", DB_URL)
os.environ.setdefault("ADMIN_EMAIL", ADMIN_EMAIL)
os.environ.setdefault("ADMIN_PASSWORD", ADMIN_PASSWORD)

if DB_PATH.exists():
    DB_PATH.unlink()


def pytest_sessionfinish(session, exitstatus):
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
        except OSError:
            pass
