import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="visionguard-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["CACHE_DIR"] = f"{_tmp}/cache"
os.environ["STORAGE_DIR"] = f"{_tmp}/storage"

import pytest  # noqa: E402

from app.db import Base, SessionLocal, engine, init_db  # noqa: E402


@pytest.fixture()
def db():
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
