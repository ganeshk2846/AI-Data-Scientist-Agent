"""
API endpoints for database connection, testing, file upload, and active database management.
Enforces read-only database connections and automatically triggers schema preparation.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
import sqlite3
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from backend.app.core.config import REPO_ROOT, settings
from backend.app.core.contracts import (
    ActiveDatabaseConfig,
    ConnectionStatus,
    SupportedEngine,
)
from backend.app.core.errors import DatabaseError
from backend.app.core.logging import logger
from backend.app.core.models import APIResponse
from backend.app.db.adapters.mysql import MySQLAdapter
from backend.app.db.adapters.postgres import PostgresAdapter
from backend.app.db.adapters.sqlite import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.db.security import (
    decrypt_connection_params,
    encrypt_connection_params,
)
from backend.app.schema.job import job_manager
from backend.app.schema.models import PreparationJobState

router = APIRouter(prefix="/db", tags=["Database Connection"])

SQLITE_HEADER = b"SQLite format 3\x00"
UPLOADS_DIR = REPO_ROOT / "data" / "uploads"


class DatabaseTestRequest(BaseModel):
    engine: SupportedEngine
    name: Optional[str] = "test_connection"
    file_path: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl: Optional[bool] = False


class DatabaseConnectRequest(BaseModel):
    engine: SupportedEngine
    name: str = Field(..., min_length=1, description="Display name for this database connection")
    file_path: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl: Optional[bool] = False


class DatabaseStatusInfo(BaseModel):
    name: str
    engine: str
    status: str
    fingerprint: Optional[str] = None
    read_only: bool = True
    table_count: int = 0
    row_count: int = 0
    connected: bool = False


class SavedDatabaseInfo(BaseModel):
    id: str
    name: str
    engine: str
    fingerprint: Optional[str] = None
    is_active: bool = False
    created_at: Optional[str] = None


@router.get(
    "/status",
    response_model=APIResponse[DatabaseStatusInfo],
    summary="Get active database connection status",
)
async def get_database_status(request: Request) -> APIResponse[DatabaseStatusInfo]:
    """Returns details of the currently active database."""
    request_id = getattr(request.state, "request_id", None)
    config = db_manager.get_active_config()

    if not config or config.status == ConnectionStatus.DISCONNECTED:
        data = DatabaseStatusInfo(
            name="None",
            engine="none",
            status="DISCONNECTED",
            connected=False,
            read_only=True,
        )
        return APIResponse(success=True, data=data, request_id=request_id)

    try:
        adapter = db_manager.get_active_adapter()
        tables = adapter.get_table_names()
        table_count = len(tables)
        row_count = sum(adapter.get_table_row_count(t) for t in tables) if table_count <= 100 else 0
        connected = adapter.is_connected
        fp = adapter.compute_fingerprint()
    except Exception as e:
        logger.debug(f"Error fetching active adapter details: {e}")
        table_count = 0
        row_count = 0
        connected = False
        fp = config.fingerprint

    data = DatabaseStatusInfo(
        name=config.name,
        engine=config.engine.value,
        status="CONNECTED" if connected else config.status.value,
        fingerprint=fp,
        read_only=config.read_only,
        table_count=table_count,
        row_count=row_count,
        connected=connected,
    )
    return APIResponse(success=True, data=data, request_id=request_id)


@router.get(
    "/saved",
    response_model=APIResponse[List[SavedDatabaseInfo]],
    summary="List saved database configurations",
)
async def get_saved_databases(request: Request) -> APIResponse[List[SavedDatabaseInfo]]:
    """Returns saved database connections without exposing passwords."""
    request_id = getattr(request.state, "request_id", None)
    conn = sqlite3.connect(str(settings.resolved_app_db_path))
    conn.row_factory = sqlite3.Row
    saved: List[SavedDatabaseInfo] = []
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, engine, fingerprint, is_active, created_at FROM saved_databases ORDER BY updated_at DESC;")
        rows = cur.fetchall()
        for r in rows:
            saved.append(
                SavedDatabaseInfo(
                    id=r["id"],
                    name=r["name"],
                    engine=r["engine"],
                    fingerprint=r["fingerprint"],
                    is_active=bool(r["is_active"]),
                    created_at=str(r["created_at"]),
                )
            )
    finally:
        conn.close()

    return APIResponse(success=True, data=saved, request_id=request_id)


@router.post(
    "/test",
    response_model=APIResponse[Dict[str, Any]],
    summary="Test database connection without activating",
)
async def test_database_connection(req: DatabaseTestRequest, request: Request) -> APIResponse[Dict[str, Any]]:
    """Tests connectivity and counts discovered tables in read-only mode."""
    request_id = getattr(request.state, "request_id", None)

    if req.engine == SupportedEngine.SQLITE:
        file_path_str = req.file_path or ""
        clean_path = Path(file_path_str)
        if not clean_path.is_absolute():
            clean_path = REPO_ROOT / clean_path
        clean_path = clean_path.resolve()

        if not clean_path.exists() or not clean_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SQLite file not found at: {req.file_path}",
            )

        # Validate SQLite header magic bytes
        try:
            with open(clean_path, "rb") as f:
                header = f.read(16)
            if not header.startswith(SQLITE_HEADER):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The provided file is not a valid SQLite database file.",
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot read SQLite database file: {str(e)}",
            )

        # Test read-only connect
        try:
            adapter = SQLiteAdapter(file_path=clean_path, name=req.name or "test_sqlite", read_only=True)
            adapter.connect()
            tables = adapter.get_table_names()
            adapter.disconnect()
            return APIResponse(
                success=True,
                data={
                    "engine": "sqlite",
                    "table_count": len(tables),
                    "message": f"Successfully connected to SQLite. Discovered {len(tables)} tables.",
                },
                request_id=request_id,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to SQLite: {str(e)}",
            )

    elif req.engine == SupportedEngine.POSTGRESQL:
        if not req.host or not req.database or not req.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PostgreSQL requires host, database, and username.",
            )
        try:
            adapter = PostgresAdapter(
                host=req.host,
                port=req.port or 5432,
                database=req.database,
                username=req.username,
                password=req.password,
                name=req.name or "test_postgres",
                read_only=True,
            )
            adapter.connect()
            tables = adapter.get_table_names()
            adapter.disconnect()
            return APIResponse(
                success=True,
                data={
                    "engine": "postgresql",
                    "table_count": len(tables),
                    "message": f"Successfully connected to PostgreSQL. Discovered {len(tables)} tables.",
                },
                request_id=request_id,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to PostgreSQL: {str(e)}",
            )

    elif req.engine == SupportedEngine.MYSQL:
        if not req.host or not req.database or not req.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MySQL requires host, database, and username.",
            )
        try:
            adapter = MySQLAdapter(
                host=req.host,
                port=req.port or 3306,
                database=req.database,
                username=req.username,
                password=req.password,
                name=req.name or "test_mysql",
                read_only=True,
            )
            adapter.connect()
            tables = adapter.get_table_names()
            adapter.disconnect()
            return APIResponse(
                success=True,
                data={
                    "engine": "mysql",
                    "table_count": len(tables),
                    "message": f"Successfully connected to MySQL. Discovered {len(tables)} tables.",
                },
                request_id=request_id,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to connect to MySQL: {str(e)}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported engine type: {req.engine}",
        )


@router.post(
    "/upload-sqlite",
    response_model=APIResponse[Dict[str, Any]],
    summary="Upload a SQLite database file safely",
)
async def upload_sqlite_file(
    file: UploadFile = File(...),
    request: Request = None,
) -> APIResponse[Dict[str, Any]]:
    """
    Saves an uploaded SQLite database file into data/uploads/ after validating
    file extension, magic byte header, and preventing overwrites of protected databases.
    """
    request_id = getattr(request.state, "request_id", None) if request else None

    # Sanitize filename
    filename = Path(file.filename).name
    # Remove dangerous characters
    clean_name = re.sub(r"[^a-zA-Z0-9_\.-]", "_", filename)
    if not clean_name.lower().endswith((".db", ".sqlite", ".sqlite3")):
        clean_name += ".db"

    # Block overwriting baseline databases
    if clean_name.lower() in ["ecommerce.db", "agent_app.sqlite"]:
        clean_name = f"uploaded_{int(datetime.now(timezone.utc).timestamp())}_{clean_name}"

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = UPLOADS_DIR / clean_name

    # Read first 16 bytes to verify magic header
    header = await file.read(16)
    if not header.startswith(SQLITE_HEADER):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid SQLite database (invalid header magic bytes).",
        )

    # Save to disk
    with open(target_path, "wb") as f:
        f.write(header)
        while chunk := await file.read(65536):
            f.write(chunk)

    rel_path = f"data/uploads/{clean_name}"
    file_size = target_path.stat().st_size

    return APIResponse(
        success=True,
        data={
            "file_path": rel_path,
            "filename": clean_name,
            "size_bytes": file_size,
            "message": f"Uploaded SQLite database successfully ({file_size:,} bytes).",
        },
        request_id=request_id,
    )


@router.post(
    "/connect",
    response_model=APIResponse[Dict[str, Any]],
    summary="Connect database and trigger automatic schema preparation",
)
async def connect_database(req: DatabaseConnectRequest, request: Request) -> APIResponse[Dict[str, Any]]:
    """
    Establishes read-only connection, saves configuration securely, and
    automatically triggers the 7-stage asynchronous schema preparation job.
    """
    request_id = getattr(request.state, "request_id", None)

    # Build config and credential params
    params: Dict[str, Any] = {}
    if req.engine == SupportedEngine.SQLITE:
        file_path_str = req.file_path or ""
        clean_path = Path(file_path_str)
        if not clean_path.is_absolute():
            clean_path = REPO_ROOT / clean_path
        clean_path = clean_path.resolve()

        if not clean_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SQLite file not found at: {req.file_path}",
            )

        # Verify magic header
        with open(clean_path, "rb") as f:
            header = f.read(16)
        if not header.startswith(SQLITE_HEADER):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provided file is not a valid SQLite database.",
            )

        params["file_path"] = str(clean_path)
        config = ActiveDatabaseConfig(
            id="active_db",
            name=req.name,
            engine=SupportedEngine.SQLITE,
            file_path=str(clean_path),
            read_only=True,
        )
    elif req.engine == SupportedEngine.POSTGRESQL:
        if not req.host or not req.database or not req.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PostgreSQL requires host, database, and username.",
            )
        params = {
            "host": req.host,
            "port": req.port or 5432,
            "database": req.database,
            "username": req.username,
            "password": req.password,
        }
        config = ActiveDatabaseConfig(
            id="active_db",
            name=req.name,
            engine=SupportedEngine.POSTGRESQL,
            host=req.host,
            port=req.port or 5432,
            database=req.database,
            username=req.username,
            read_only=True,
        )
    elif req.engine == SupportedEngine.MYSQL:
        if not req.host or not req.database or not req.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MySQL requires host, database, and username.",
            )
        params = {
            "host": req.host,
            "port": req.port or 3306,
            "database": req.database,
            "username": req.username,
            "password": req.password,
        }
        config = ActiveDatabaseConfig(
            id="active_db",
            name=req.name,
            engine=SupportedEngine.MYSQL,
            host=req.host,
            port=req.port or 3306,
            database=req.database,
            username=req.username,
            read_only=True,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported engine: {req.engine}",
        )

    # Connect adapter via DatabaseConnectionManager
    try:
        adapter = db_manager.connect_database(config, params)
        fingerprint = adapter.compute_fingerprint()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect to {req.engine.value} database: {str(e)}",
        )

    # Save to saved_databases table in agent_app.sqlite
    db_id = str(uuid.uuid4())
    conn = sqlite3.connect(str(settings.resolved_app_db_path))
    try:
        enc_params = encrypt_connection_params(params)
        with conn:
            # Mark other saved databases as inactive
            conn.execute("UPDATE saved_databases SET is_active = 0;")
            conn.execute(
                """
                INSERT INTO saved_databases (id, name, engine, connection_params_enc, fingerprint, is_active, updated_at)
                VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                """,
                (db_id, req.name, req.engine.value, enc_params, fingerprint),
            )
    finally:
        conn.close()

    # Automatically launch asynchronous schema preparation
    job_state = await job_manager.start_preparation_job(force_refresh=False)

    return APIResponse(
        success=True,
        data={
            "database": {
                "id": db_id,
                "name": req.name,
                "engine": req.engine.value,
                "fingerprint": fingerprint,
                "read_only": True,
                "status": "CONNECTED",
            },
            "preparation_job": job_state.model_dump(),
        },
        request_id=request_id,
    )


@router.post(
    "/activate/{database_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Activate a saved database and start preparation",
)
async def activate_saved_database(database_id: str, request: Request) -> APIResponse[Dict[str, Any]]:
    """Switches the active database connection to a previously saved configuration."""
    request_id = getattr(request.state, "request_id", None)
    conn = sqlite3.connect(str(settings.resolved_app_db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM saved_databases WHERE id = ?;", (database_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Saved database not found: {database_id}",
            )

        params = decrypt_connection_params(row["connection_params_enc"])
        engine = SupportedEngine(row["engine"])
        config = ActiveDatabaseConfig(
            id="active_db",
            name=row["name"],
            engine=engine,
            file_path=params.get("file_path"),
            host=params.get("host"),
            port=params.get("port"),
            database=params.get("database"),
            username=params.get("username"),
            read_only=True,
        )

        adapter = db_manager.connect_database(config, params)
        fingerprint = adapter.compute_fingerprint()

        # Update active flags
        with conn:
            conn.execute("UPDATE saved_databases SET is_active = 0;")
            conn.execute("UPDATE saved_databases SET is_active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (database_id,))
    finally:
        conn.close()

    # Automatically launch asynchronous schema preparation
    job_state = await job_manager.start_preparation_job(force_refresh=False)

    return APIResponse(
        success=True,
        data={
            "database": {
                "id": database_id,
                "name": config.name,
                "engine": config.engine.value,
                "fingerprint": fingerprint,
                "read_only": True,
                "status": "CONNECTED",
            },
            "preparation_job": job_state.model_dump(),
        },
        request_id=request_id,
    )


@router.post(
    "/disconnect",
    response_model=APIResponse[Dict[str, str]],
    summary="Disconnect active database",
)
async def disconnect_active_database(request: Request) -> APIResponse[Dict[str, str]]:
    """Gracefully disconnects the currently active database and invalidates catalog cache."""
    request_id = getattr(request.state, "request_id", None)
    db_manager.disconnect_database()
    return APIResponse(
        success=True,
        data={"message": "Active database disconnected successfully."},
        request_id=request_id,
    )
