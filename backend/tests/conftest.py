import os

# Unit/API tests always run against Demo Mode so live .env keys cannot change assertions.
os.environ["USE_MOCK_PROVIDERS"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_visionguard.db")

import pytest
from fastapi.testclient import TestClient

# Reload settings after forcing mock so app.core.config.settings picks it up.
from app.core import config as config_module

config_module.settings = config_module.Settings()

from app.db.init_db import init_db
from app.db.seed import seed_if_empty
from app.main import app


@pytest.fixture(scope="session")
def client():
    init_db()
    seed_if_empty()
    with TestClient(app) as c:
        yield c
