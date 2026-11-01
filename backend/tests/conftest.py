"""
Pytest configuration and test fixtures.
"""

import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure root directory is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import app
from backend.app.core.config import settings


@pytest.fixture(scope="session")
def client():
    """Provides a synchronous FastAPI TestClient."""
    with TestClient(app) as test_client:
        yield test_client
