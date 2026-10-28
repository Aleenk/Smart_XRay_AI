from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = (
    Path("/tmp/smart_xray.db")
    if os.getenv("K_SERVICE")
    else PROJECT_ROOT / "backend" / "data" / "smart_xray.db"
)
DB_PATH = Path(os.getenv("SMART_XRAY_DB_PATH", str(DEFAULT_DB_PATH)))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SESSION_HOURS = int(os.getenv("SMART_XRAY_SESSION_HOURS", "8"))
PBKDF2_ITERATIONS = 260_000
ALLOWED_ROLES = {"ADMIN", "DOCTOR", "TECHNICIAN"}

security = HTTPBearer(auto_error=False)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    if not password or len(password) < 10:
        raise ValueError("Password must contain at least 10 characters.")

    if salt_hex is None:
        salt = secrets.token_bytes(16)
        salt_hex = salt.hex()
    else:
        salt = bytes.fromhex(salt_hex)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    ).hex()
    return salt_hex, password_hash


def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    _, actual_hash = hash_password(password, salt_hex)
    return secrets.compare_digest(actual_hash, expected_hash)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def image_digest(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _ensure_schema() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('ADMIN', 'DOCTOR', 'TECHNICIAN')),
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                previous_hash TEXT NOT NULL DEFAULT '',
                entry_hash TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS analysis_records (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                image_sha256 TEXT NOT NULL,
                content_type TEXT NOT NULL,
                detected_findings TEXT NOT NULL,
                scores TEXT NOT NULL,
                no_selected_finding_detected INTEGER NOT NULL CHECK (no_selected_finding_detected IN (0, 1)),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_token_hash
                ON sessions(token_hash);

            CREATE INDEX IF NOT EXISTS idx_audit_created_at
                ON audit_log(created_at);

            CREATE INDEX IF NOT EXISTS idx_records_created_at
                ON analysis_records(created_at);
            """
        )


def _generated_password(label: str) -> str:
    password = secrets.token_urlsafe(18)
    print(
        f"[Smart X-Ray AI] No environment password was provided for {label}. "
        f"A temporary password was generated for this process: {password}"
    )
    return password


def _seed_user(username: str, role: str, env_name: str) -> None:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if existing:
            return

        password = os.getenv(env_name) or _generated_password(username)
        salt_hex, password_hash = hash_password(password)

        conn.execute(
            """
            INSERT INTO users (
                username, password_salt, password_hash, role, active, created_at
            ) VALUES (?, ?, ?, ?, 1, ?)
            """,
            (
                username,
                salt_hex,
                password_hash,
                role,
                utc_now_iso(),
            ),
        )


def initialize_security() -> None:
    _ensure_schema()

    _seed_user(
        os.getenv("SMART_XRAY_ADMIN_USERNAME", "admin"),
        "ADMIN",
        "SMART_XRAY_ADMIN_PASSWORD",
    )
    _seed_user(
        os.getenv("SMART_XRAY_DOCTOR_USERNAME", "doctor"),
        "DOCTOR",
        "SMART_XRAY_DOCTOR_PASSWORD",
    )
    _seed_user(
        os.getenv("SMART_XRAY_TECHNICIAN_USERNAME", "technician"),
        "TECHNICIAN",
        "SMART_XRAY_TECHNICIAN_PASSWORD",
    )

    log_event(
        username="SYSTEM",
        role="SYSTEM",
        action="APPLICATION_START",
        status="SUCCESS",
        details="Smart X-Ray AI backend started.",
    )


def _latest_audit_hash(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row["entry_hash"] if row else ""


def _audit_hash(
    created_at: str,
    username: str,
    role: str,
    action: str,
    status: str,
    details: str,
    previous_hash: str,
) -> str:
    material = "|".join(
        [
            created_at,
            username,
            role,
            action,
            status,
            details,
            previous_hash,
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def log_event(
    username: str,
    role: str,
    action: str,
    status: str,
    details: str = "",
) -> None:
    clean_details = (details or "").replace("\n", " ").strip()[:1000]
    created_at = utc_now_iso()

    with get_connection() as conn:
        previous_hash = _latest_audit_hash(conn)
        entry_hash = _audit_hash(
            created_at,
            username,
            role,
            action,
            status,
            clean_details,
            previous_hash,
        )
        conn.execute(
            """
            INSERT INTO audit_log (
                created_at, username, role, action, status, details,
                previous_hash, entry_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                username,
                role,
                action,
                status,
                clean_details,
                previous_hash,
                entry_hash,
            ),
        )


def verify_audit_chain() -> tuple[bool, str]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT created_at, username, role, action, status, details,
                   previous_hash, entry_hash
            FROM audit_log
            ORDER BY id ASC
            """
        ).fetchall()

    expected_previous = ""
    for index, row in enumerate(rows, start=1):
        if row["previous_hash"] != expected_previous:
            return False, f"Audit chain broken before entry {index}."

        expected_hash = _audit_hash(
            row["created_at"],
            row["username"],
            row["role"],
            row["action"],
            row["status"],
            row["details"],
            row["previous_hash"],
        )

        if not secrets.compare_digest(expected_hash, row["entry_hash"]):
            return False, f"Audit entry {index} was modified."

        expected_previous = row["entry_hash"]

    return True, f"Audit chain verified successfully ({len(rows)} entries)."


def find_user(username: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, username, password_salt, password_hash, role, active, created_at
            FROM users
            WHERE username = ?
            """,
            (username.strip(),),
        ).fetchone()
    return dict(row) if row else None


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "role": row["role"],
        "active": bool(row["active"]),
        "created_at": row["created_at"],
    }


def authenticate_user(username: str, password: str) -> dict[str, Any] | None:
    user = find_user(username)
    if not user or not user["active"]:
        return None

    if not verify_password(
        password,
        user["password_salt"],
        user["password_hash"],
    ):
        return None

    return user


def create_session(user_id: int) -> tuple[str, str]:
    token = secrets.token_urlsafe(48)
    token_hash = token_digest(token)
    created_at = utc_now()
    expires_at = created_at + timedelta(hours=SESSION_HOURS)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions (
                user_id, token_hash, created_at, expires_at, revoked_at
            ) VALUES (?, ?, ?, ?, NULL)
            """,
            (
                user_id,
                token_hash,
                created_at.isoformat(),
                expires_at.isoformat(),
            ),
        )

    return token, expires_at.isoformat()


def revoke_session(token: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET revoked_at = ?
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (utc_now_iso(), token_digest(token)),
        )


def _session_user(token: str) -> dict[str, Any] | None:
    digest = token_digest(token)

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                u.id, u.username, u.role, u.active, u.created_at,
                s.expires_at, s.revoked_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (digest,),
        ).fetchone()

    if not row:
        return None

    result = dict(row)

    if not result["active"] or result["revoked_at"]:
        return None

    expires_at = datetime.fromisoformat(result["expires_at"])
    if expires_at <= utc_now():
        return None

    return result


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = _session_user(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Session is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(*roles: str):
    allowed = set(roles)

    def dependency(
        user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if user["role"] not in allowed:
            log_event(
                username=user["username"],
                role=user["role"],
                action="ACCESS_DENIED",
                status="DENIED",
                details=f"Required role: {', '.join(sorted(allowed))}",
            )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action.",
            )
        return user

    return dependency


def create_user(
    username: str,
    password: str,
    role: str,
) -> dict[str, Any]:
    username = username.strip()
    role = role.strip().upper()

    if len(username) < 3:
        raise ValueError("Username must contain at least 3 characters.")

    if role not in ALLOWED_ROLES:
        raise ValueError(
            "Role must be ADMIN, DOCTOR, or TECHNICIAN."
        )

    salt_hex, password_hash = hash_password(password)

    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (
                    username, password_salt, password_hash, role, active, created_at
                ) VALUES (?, ?, ?, ?, 1, ?)
                """,
                (
                    username,
                    salt_hex,
                    password_hash,
                    role,
                    utc_now_iso(),
                ),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ValueError("A user with this username already exists.") from exc

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, username, role, active, created_at
            FROM users WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    return dict(row)


def list_users() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, username, role, active, created_at
            FROM users
            ORDER BY id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def set_user_active(user_id: int, active: bool) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, role, active, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        if not row:
            raise ValueError("User not found.")

        conn.execute(
            "UPDATE users SET active = ? WHERE id = ?",
            (1 if active else 0, user_id),
        )

        updated = conn.execute(
            "SELECT id, username, role, active, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    return dict(updated)


def list_audit_events(limit: int = 200) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 1000))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, username, role, action, status, details,
                   previous_hash, entry_hash
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def create_analysis_record(
    user: dict[str, Any],
    file_bytes: bytes,
    content_type: str,
    result: dict[str, Any],
) -> str:
    record_id = str(uuid4())

    detected_findings = result.get("detected_findings", [])
    scores = result.get("predictions", result.get("scores", {}))
    no_finding = bool(result.get("no_selected_finding_detected", False))

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO analysis_records (
                id, created_at, user_id, username, role,
                image_sha256, content_type, detected_findings, scores,
                no_selected_finding_detected
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                utc_now_iso(),
                int(user["id"]),
                user["username"],
                user["role"],
                image_digest(file_bytes),
                content_type,
                json.dumps(detected_findings),
                json.dumps(scores),
                1 if no_finding else 0,
            ),
        )

    return record_id


def list_analysis_records(limit: int = 200) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 1000))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, username, role, image_sha256,
                   content_type, detected_findings, scores,
                   no_selected_finding_detected
            FROM analysis_records
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    records = []
    for row in rows:
        item = dict(row)
        item["detected_findings"] = json.loads(item["detected_findings"])
        item["scores"] = json.loads(item["scores"])
        item["no_selected_finding_detected"] = bool(
            item["no_selected_finding_detected"]
        )
        records.append(item)

    return records


def get_analysis_record(record_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, created_at, username, role, image_sha256,
                   content_type, detected_findings, scores,
                   no_selected_finding_detected
            FROM analysis_records
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()

    if not row:
        return None

    item = dict(row)
    item["detected_findings"] = json.loads(item["detected_findings"])
    item["scores"] = json.loads(item["scores"])
    item["no_selected_finding_detected"] = bool(
        item["no_selected_finding_detected"]
    )
    return item
