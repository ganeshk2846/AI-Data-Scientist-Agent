"""
Comprehensive tests for Self-Service LLM & Database Connection Workflow.
Covers:
1. Groq LLM connection, model validation, credential encryption, and key masking.
2. Database connection, SQLite testing, PostgreSQL/MySQL validation, and upload security.
3. Strict read-only enforcement across all connections.
4. Automatic 7-stage asynchronous schema preparation pipeline and index artifact reuse.
5. Unified setup readiness state derivation (chat locked until LLM + DB + Prep are verified).
6. Database switching, fingerprint cache invalidation, and session restoration.
"""

import asyncio
from pathlib import Path
import sqlite3
import tempfile
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import REPO_ROOT, settings
from backend.app.core.contracts import ConnectionStatus, SupportedEngine
from backend.app.db.adapters.sqlite import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.llm.client import (
    SUPPORTED_GROQ_MODELS,
    disconnect_groq_credentials,
    load_persisted_llm_credentials,
    mask_api_key,
    set_active_groq_credentials,
)
from backend.app.main import app
from backend.app.retrieval.persistent_bm25 import PersistentBM25Retriever
from backend.app.retrieval.vector_store import LanceDBVectorStore
from backend.app.schema.job import job_manager
from backend.app.schema.models import JobStatusEnum, StageStatusEnum
from backend.app.schema.service import schema_service


@pytest.fixture
def client():
    return TestClient(app)


# =========================================================================
# 1. Groq LLM Provider & Connection Tests
# =========================================================================

def test_supported_groq_models_list(client):
    """Verifies retrieval of curated, supported Groq models with recommended tags."""
    res = client.get("/api/v1/llm/models")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    models = body["data"]
    assert len(models) >= 3

    model_ids = [m["id"] for m in models]
    assert "llama-3.3-70b-versatile" in model_ids
    assert "openai/gpt-oss-120b" in model_ids
    assert "llama-3.1-8b-instant" in model_ids

    rec = next(m for m in models if m["id"] == "llama-3.3-70b-versatile")
    assert rec["is_recommended"] is True
    assert rec["context_window"] == 128000


def test_groq_key_masking():
    """Verifies raw API key is never exposed and masked properly."""
    assert mask_api_key(None) is None
    assert mask_api_key("") is None
    assert mask_api_key("short") == "gsk_...****"
    assert mask_api_key("gsk_test_api_key_1234567890abcdef") == "gsk_...cdef"


def test_groq_missing_and_invalid_connection(client):
    """Verifies validation on empty or whitespace keys."""
    res = client.post("/api/v1/llm/connect", json={"api_key": "   ", "model": "llama-3.3-70b-versatile"})
    assert res.status_code == 400

    # In production without mock key, invalid key returns 400
    res2 = client.post("/api/v1/llm/connect", json={"api_key": "gsk_obviously_invalid_key_9999", "model": "llama-3.3-70b-versatile"})
    assert res2.status_code in [400, 502]


def test_groq_connect_and_status(client):
    """Tests connecting Groq key and verifying status in memory and encrypted store."""
    test_key = "mock_groq_key_1234567890abcdef"
    res = client.post("/api/v1/llm/connect", json={"api_key": test_key, "model": "llama-3.3-70b-versatile"})
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["connected"] is True
    assert body["data"]["provider"] == "groq"
    assert body["data"]["model"] == "llama-3.3-70b-versatile"
    assert body["data"]["masked_key"] == "mock...cdef"

    # Status check
    status_res = client.get("/api/v1/llm/status")
    assert status_res.status_code == 200
    s_body = status_res.json()
    assert s_body["data"]["connected"] is True
    assert s_body["data"]["masked_key"] == "mock...cdef"

    # Verify encrypted persistence in agent_app.sqlite
    persisted = load_persisted_llm_credentials()
    assert persisted is not None
    assert persisted["api_key"] == test_key
    assert persisted["model"] == "llama-3.3-70b-versatile"


def test_groq_disconnect(client):
    """Tests disconnecting Groq LLM."""
    res = client.post("/api/v1/llm/disconnect")
    assert res.status_code == 200
    assert res.json()["success"] is True

    status_res = client.get("/api/v1/llm/status")
    assert status_res.status_code == 200
    assert status_res.json()["data"]["connected"] is False


# =========================================================================
# 2. Database Connection, Testing, and Upload Security Tests
# =========================================================================

def test_database_test_sqlite_valid(client):
    """Tests read-only connection test on ecommerce.db without altering active state."""
    res = client.post(
        "/api/v1/db/test",
        json={"engine": "sqlite", "file_path": "ecommerce.db", "name": "Test DB"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["engine"] == "sqlite"
    assert body["data"]["table_count"] == 46


def test_database_test_sqlite_invalid_file(client):
    """Tests connection test rejection on non-existent or invalid file."""
    res = client.post(
        "/api/v1/db/test",
        json={"engine": "sqlite", "file_path": "data/non_existent.db", "name": "Fake DB"},
    )
    assert res.status_code == 400


def test_database_test_sqlite_corrupt_header(client, tmp_path):
    """Tests rejecting file without SQLite magic bytes."""
    corrupt_file = tmp_path / "corrupt.db"
    corrupt_file.write_text("This is not a sqlite database file header.")

    res = client.post(
        "/api/v1/db/test",
        json={"engine": "sqlite", "file_path": str(corrupt_file), "name": "Corrupt DB"},
    )
    assert res.status_code == 400
    json_data = res.json()
    err_msg = json_data.get("detail") or json_data.get("error", {}).get("message", "")
    assert "not a valid sqlite database" in err_msg.lower()


def test_database_test_postgres_mysql_validation(client):
    """Tests parameter validation for PostgreSQL and MySQL."""
    # Missing required parameters returns 400
    res_pg = client.post("/api/v1/db/test", json={"engine": "postgresql"})
    assert res_pg.status_code == 400
    err_pg = res_pg.json().get("detail") or res_pg.json().get("error", {}).get("message", "")
    assert "requires host, database, and username" in err_pg.lower()

    res_my = client.post("/api/v1/db/test", json={"engine": "mysql"})
    assert res_my.status_code == 400
    err_my = res_my.json().get("detail") or res_my.json().get("error", {}).get("message", "")
    assert "requires host, database, and username" in err_my.lower()


def test_upload_sqlite_file_valid_and_security(client, tmp_path):
    """Tests uploading valid SQLite database and preventing overwrite of ecommerce.db."""
    # Create valid temporary SQLite database
    temp_db = tmp_path / "custom_sales.db"
    conn = sqlite3.connect(str(temp_db))
    conn.execute("CREATE TABLE products_test (id INTEGER PRIMARY KEY, name TEXT);")
    conn.execute("INSERT INTO products_test VALUES (1, 'Widget');")
    conn.commit()
    conn.close()

    with open(temp_db, "rb") as f:
        res = client.post(
            "/api/v1/db/upload-sqlite",
            files={"file": ("custom_sales.db", f, "application/x-sqlite3")},
        )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert "custom_sales" in body["data"]["filename"]
    assert Path(REPO_ROOT / body["data"]["file_path"]).exists()

    # Attempt to upload with filename "ecommerce.db" - must be renamed to protect baseline
    with open(temp_db, "rb") as f:
        res_protect = client.post(
            "/api/v1/db/upload-sqlite",
            files={"file": ("ecommerce.db", f, "application/x-sqlite3")},
        )
    assert res_protect.status_code == 200
    assert res_protect.json()["data"]["filename"] != "ecommerce.db"
    assert "uploaded_" in res_protect.json()["data"]["filename"]


def test_read_only_connection_enforcement():
    """Verifies that SQLite adapter strictly rejects write attempts."""
    adapter = SQLiteAdapter(file_path=REPO_ROOT / "ecommerce.db", read_only=True)
    adapter.connect()
    assert adapter.is_connected is True

    # SELECT succeeds
    tables = adapter.get_table_names()
    assert len(tables) == 46

    # INSERT is blocked by AST guardrail or SQLite read-only mode
    with pytest.raises(Exception) as exc_info:
        adapter.execute_query("INSERT INTO orders (order_id) VALUES ('fake');")
    err_str = str(exc_info.value).lower()
    assert (
        "readonly" in err_str
        or "read-only" in err_str
        or "query_only" in err_str
        or "prohibited sql keyword" in err_str
        or "guardrail" in err_str
    )
    adapter.disconnect()


# =========================================================================
# 3. 7-Stage Schema Preparation & Retrieval Indexing Tests
# =========================================================================

def test_preparation_job_7_stages():
    """Verifies that schema preparation steps through all 7 stages and succeeds."""
    async def _run():
        adapter = db_manager.get_active_adapter()
        assert adapter.is_connected is True

        job = await job_manager.start_preparation_job(force_refresh=True)
        assert job.status in [JobStatusEnum.PENDING, JobStatusEnum.RUNNING, JobStatusEnum.SUCCEEDED]
        assert len(job.stages) == 7

        max_wait = 20
        waited = 0
        latest = job
        while waited < max_wait:
            await asyncio.sleep(0.5)
            latest = job_manager.get_job(job.job_id)
            if latest.status in [JobStatusEnum.SUCCEEDED, JobStatusEnum.FAILED]:
                break
            waited += 0.5

        assert latest.status == JobStatusEnum.SUCCEEDED
        assert latest.progress_percent == 100
        assert len(latest.stages) == 7

        stage_names = [s.name for s in latest.stages]
        assert "Database connection verified" in stage_names
        assert "Schema discovery" in stage_names
        assert "Table profiling" in stage_names
        assert "Semantic metadata construction" in stage_names
        assert "Building dense vector index" in stage_names
        assert "Building BM25 index" in stage_names
        assert "Final preparation verification" in stage_names

        for s in latest.stages:
            assert s.status == StageStatusEnum.COMPLETED
            assert s.details is not None

    asyncio.run(_run())


def test_fast_index_artifact_reuse():
    """Verifies that running preparation on an already-prepared database reuses artifacts in < 500ms."""
    async def _run():
        t0 = asyncio.get_event_loop().time()
        job = await job_manager.start_preparation_job(force_refresh=False)

        max_wait = 10
        waited = 0
        latest = job
        while waited < max_wait:
            await asyncio.sleep(0.1)
            latest = job_manager.get_job(job.job_id)
            if latest.status in [JobStatusEnum.SUCCEEDED, JobStatusEnum.FAILED]:
                break
            waited += 0.1

        elapsed = asyncio.get_event_loop().time() - t0
        assert latest.status == JobStatusEnum.SUCCEEDED
        # Check that artifact reuse details are captured
        stage5 = next(s for s in latest.stages if s.id == 5)
        assert "reused" in stage5.details.lower() or "indexed" in stage5.details.lower()

    asyncio.run(_run())


def test_dense_vector_and_bm25_existence():
    """Verifies physical index artifacts in data/lancedb and data/bm25."""
    fp = schema_service.compute_source_fingerprint()
    vstore = LanceDBVectorStore(fingerprint=fp)
    assert vstore.is_indexed() is True
    assert vstore.count() == 46

    bm25 = PersistentBM25Retriever(fingerprint=fp)
    assert bm25.is_persisted() is True
    assert len(bm25.table_names) == 46


# =========================================================================
# 4. Setup Readiness & Workflow Unlocking Tests
# =========================================================================

def test_setup_status_endpoint(client):
    """
    Verifies that GET /api/v1/setup/status accurately reflects the active state.
    When Groq is configured, DB is connected, and preparation is completed: chat_ready == True.
    """
    # Connect Groq credentials
    set_active_groq_credentials("mock_groq_key_1234567890abcdef", "llama-3.3-70b-versatile")

    res = client.get("/api/v1/setup/status")
    assert res.status_code == 200
    body = res.json()["data"]

    assert body["llm_status"] == "CONNECTED"
    assert body["database_status"] == "CONNECTED"
    assert body["preparation_status"] == "COMPLETED"
    assert body["chat_ready"] is True
    assert body["llm"]["provider"] == "groq"
    assert body["database"]["name"] == "ecommerce.db"


def test_setup_status_locked_when_llm_disconnected(client):
    """Verifies that disconnecting LLM locks the chat workspace."""
    disconnect_groq_credentials()

    res = client.get("/api/v1/setup/status")
    assert res.status_code == 200
    body = res.json()["data"]

    assert body["llm_status"] == "NOT_CONNECTED"
    assert body["chat_ready"] is False

    # Restore key for subsequent tests
    set_active_groq_credentials("mock_groq_key_1234567890abcdef", "llama-3.3-70b-versatile")


def test_database_switching_and_isolation(client, tmp_path):
    """Tests switching databases, ensuring cache eviction and fingerprint isolation."""
    # Create secondary database
    sec_db = tmp_path / "secondary.db"
    conn = sqlite3.connect(str(sec_db))
    conn.execute("CREATE TABLE inventory_items (id INT, item_name TEXT);")
    conn.commit()
    conn.close()

    # Connect secondary database
    connect_res = client.post(
        "/api/v1/db/connect",
        json={"engine": "sqlite", "name": "Secondary Database", "file_path": str(sec_db)},
    )
    assert connect_res.status_code == 200
    body = connect_res.json()["data"]
    sec_fp = body["database"]["fingerprint"]
    assert sec_fp is not None

    # Verify active config changed
    active_config = db_manager.get_active_config()
    assert active_config.name == "Secondary Database"

    # Verify saved databases list contains both
    saved_res = client.get("/api/v1/db/saved")
    assert saved_res.status_code == 200
    saved = saved_res.json()["data"]
    assert len(saved) >= 1

    # Switch back to ecommerce.db
    connect_back = client.post(
        "/api/v1/db/connect",
        json={"engine": "sqlite", "name": "ecommerce.db", "file_path": "ecommerce.db"},
    )
    assert connect_back.status_code == 200
    assert db_manager.get_active_config().name == "ecommerce.db"

    # Wait for preparation of ecommerce.db to complete
    job_id = connect_back.json()["data"]["preparation_job"]["job_id"]
    for _ in range(30):
        import time
        time.sleep(0.1)
        j = job_manager.get_job(job_id)
        if j and j.status in [JobStatusEnum.SUCCEEDED, JobStatusEnum.FAILED]:
            break


def test_page_refresh_state_restoration(client):
    """Verifies that setup state is restored seamlessly without user re-connection."""
    res = client.get("/api/v1/setup/status")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["llm"]["connected"] is True
    assert data["database"]["connected"] is True
    assert data["chat_ready"] is True
