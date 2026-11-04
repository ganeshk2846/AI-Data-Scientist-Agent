"""
Pytest configuration and test fixtures.
"""

import os
import sys
from pathlib import Path

# Enforce testing environment for automated test suites
os.environ["APP_ENV"] = "testing"

import pytest
from fastapi.testclient import TestClient

# Ensure root directory is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import app
from backend.app.core.config import settings

settings.APP_ENV = "testing"


@pytest.fixture(scope="session")
def client():
    """Provides a synchronous FastAPI TestClient."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module", autouse=True)
def restore_baseline_database():
    """
    Keeps tests isolated from one another's database connections.

    Several tests connect a temporary fixture database (test_orders, test_users)
    to exercise switching. Without this, that connection stays active and every
    later test sees a two-table warehouse, which looks like a code failure but is
    leaked state. The restore runs per module, so a module that sets up its own
    database in a module-scoped fixture is left alone while it runs.
    """
    yield

    from backend.app.core.contracts import ActiveDatabaseConfig, SupportedEngine
    from backend.app.db.manager import db_manager

    baseline = settings.resolved_ecommerce_db_path
    if not baseline.exists():
        return
    try:
        adapter = db_manager.get_active_adapter()
        active_path = getattr(adapter, "file_path", None) or getattr(adapter, "database_path", None)
        if active_path and Path(str(active_path)).resolve() == baseline.resolve():
            return
    except Exception:
        pass

    try:
        db_manager.connect_database(
            ActiveDatabaseConfig(
                name=baseline.name,
                engine=SupportedEngine.SQLITE,
                file_path=str(baseline),
            )
        )
    except Exception:
        pass


@pytest.fixture(autouse=True)
def restore_llm_credentials():
    """
    Keeps one test's LLM credentials out of every later test.

    Connecting a key through the setup endpoint rewrites the global settings and
    replaces the cached provider, so a dummy key used by one test was still in
    place for the rest of the session and every later Groq call failed with 401.
    """
    import backend.app.llm.client as llm_client

    saved_key = settings.GROQ_API_KEY
    saved_model = settings.GROQ_MODEL
    saved_provider = llm_client._active_groq_provider
    try:
        yield
    finally:
        settings.GROQ_API_KEY = saved_key
        settings.GROQ_MODEL = saved_model
        llm_client._active_groq_provider = saved_provider
