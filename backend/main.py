from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.model.inference import generate_gradcam, predict_xray
from backend.security import (
    ALLOWED_ROLES,
    authenticate_user,
    create_analysis_record,
    create_session,
    create_user,
    get_analysis_record,
    get_current_user,
    initialize_security,
    list_analysis_records,
    list_audit_events,
    list_users,
    log_event,
    public_user,
    require_roles,
    revoke_session,
    security,
    set_user_active,
    verify_audit_chain,
)
from backend.utils.image_utils import prepare_xray_image


app = FastAPI(
    title="Smart X-Ray AI",
    description="AI-assisted chest X-ray analysis prototype",
    version="2.0.0",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"

initialize_security()

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str


class UserActiveRequest(BaseModel):
    active: bool


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Smart X-Ray AI",
        "version": "2.0.0",
    }


@app.post("/auth/login")
def login(payload: LoginRequest):
    user = authenticate_user(payload.username, payload.password)

    if not user:
        log_event(
            username=payload.username.strip() or "UNKNOWN",
            role="UNKNOWN",
            action="LOGIN",
            status="FAILED",
            details="Invalid credentials or inactive user.",
        )
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token, expires_at = create_session(int(user["id"]))

    log_event(
        username=user["username"],
        role=user["role"],
        action="LOGIN",
        status="SUCCESS",
        details="Authenticated successfully.",
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "user": public_user(user),
    }


@app.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user=Depends(get_current_user),
):
    revoke_session(credentials.credentials)

    log_event(
        username=user["username"],
        role=user["role"],
        action="LOGOUT",
        status="SUCCESS",
        details="Session revoked.",
    )

    return {"status": "logged_out"}


@app.get("/auth/me")
def me(user=Depends(get_current_user)):
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "active": bool(user["active"]),
    }


@app.get("/admin/users")
def admin_list_users(admin=Depends(require_roles("ADMIN"))):
    log_event(
        username=admin["username"],
        role=admin["role"],
        action="USER_LIST_VIEW",
        status="SUCCESS",
        details="Administrator viewed the user list.",
    )
    return {"users": list_users()}


@app.post("/admin/users", status_code=201)
def admin_create_user(
    payload: CreateUserRequest,
    admin=Depends(require_roles("ADMIN")),
):
    role = payload.role.strip().upper()

    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail="Role must be ADMIN, DOCTOR, or TECHNICIAN.",
        )

    try:
        user = create_user(payload.username, payload.password, role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_event(
        username=admin["username"],
        role=admin["role"],
        action="USER_CREATED",
        status="SUCCESS",
        details=f"Created account '{user['username']}' with role {user['role']}.",
    )

    return {"user": user}


@app.patch("/admin/users/{user_id}/active")
def admin_set_user_active(
    user_id: int,
    payload: UserActiveRequest,
    admin=Depends(require_roles("ADMIN")),
):
    if int(admin["id"]) == user_id and not payload.active:
        raise HTTPException(
            status_code=400,
            detail="The currently signed-in administrator cannot deactivate their own account.",
        )

    try:
        user = set_user_active(user_id, payload.active)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    log_event(
        username=admin["username"],
        role=admin["role"],
        action="USER_STATUS_CHANGED",
        status="SUCCESS",
        details=(
            f"Account '{user['username']}' active status changed to "
            f"{bool(user['active'])}."
        ),
    )

    return {"user": user}


@app.get("/audit")
def get_audit(
    limit: int = Query(default=200, ge=1, le=1000),
    admin=Depends(require_roles("ADMIN")),
):
    events = list_audit_events(limit)

    log_event(
        username=admin["username"],
        role=admin["role"],
        action="AUDIT_VIEW",
        status="SUCCESS",
        details=f"Viewed up to {limit} audit entries.",
    )

    return {"events": events}


@app.get("/audit/verify")
def verify_audit(admin=Depends(require_roles("ADMIN"))):
    valid, message = verify_audit_chain()

    log_event(
        username=admin["username"],
        role=admin["role"],
        action="AUDIT_VERIFY",
        status="SUCCESS" if valid else "FAILED",
        details=message,
    )

    return {"valid": valid, "message": message}


@app.get("/audit/export")
def export_audit(admin=Depends(require_roles("ADMIN"))):
    events = list_audit_events(1000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "created_at",
            "username",
            "role",
            "action",
            "status",
            "details",
            "previous_hash",
            "entry_hash",
        ]
    )

    for event in reversed(events):
        writer.writerow(
            [
                event["id"],
                event["created_at"],
                event["username"],
                event["role"],
                event["action"],
                event["status"],
                event["details"],
                event["previous_hash"],
                event["entry_hash"],
            ]
        )

    log_event(
        username=admin["username"],
        role=admin["role"],
        action="AUDIT_EXPORT",
        status="SUCCESS",
        details="Audit Trail exported as CSV.",
    )

    payload = output.getvalue().encode("utf-8-sig")

    return StreamingResponse(
        iter([payload]),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="smart_xray_audit.csv"'
        },
    )


@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
    user=Depends(require_roles("ADMIN", "DOCTOR", "TECHNICIAN")),
):
    try:
        if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
            log_event(
                username=user["username"],
                role=user["role"],
                action="XRAY_ANALYSIS",
                status="REJECTED",
                details="Unsupported file type.",
            )
            raise HTTPException(
                status_code=400,
                detail="Only PNG and JPEG images are supported.",
            )

        file_bytes = await file.read()

        if not file_bytes:
            log_event(
                username=user["username"],
                role=user["role"],
                action="XRAY_ANALYSIS",
                status="REJECTED",
                details="Empty upload.",
            )
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        image_data = prepare_xray_image(file_bytes)
        image = image_data["image"]
        result = predict_xray(image)

        record_id = create_analysis_record(
            user=user,
            file_bytes=file_bytes,
            content_type=file.content_type or "application/octet-stream",
            result=result,
        )

        log_event(
            username=user["username"],
            role=user["role"],
            action="XRAY_ANALYSIS",
            status="SUCCESS",
            details=(
                f"Analysis record {record_id} created; "
                f"{len(result.get('detected_findings', []))} selected finding(s)."
            ),
        )

        return {
            "filename": file.filename,
            "record_id": record_id,
            **result,
        }

    except HTTPException:
        raise

    except Exception as exc:
        print("Prediction error:", type(exc).__name__, repr(exc))

        log_event(
            username=user["username"],
            role=user["role"],
            action="XRAY_ANALYSIS",
            status="FAILED",
            details=f"Server error type: {type(exc).__name__}.",
        )

        raise HTTPException(
            status_code=500,
            detail="An error occurred while analyzing the X-ray.",
        ) from exc


@app.post("/gradcam")
async def gradcam(
    file: UploadFile = File(...),
    finding: str = Form(...),
    user=Depends(require_roles("ADMIN", "DOCTOR", "TECHNICIAN")),
):
    try:
        if file.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
            raise HTTPException(
                status_code=400,
                detail="Only PNG and JPEG images are supported.",
            )

        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        image_data = prepare_xray_image(file_bytes)
        image = image_data["image"]
        result = generate_gradcam(image, finding)

        log_event(
            username=user["username"],
            role=user["role"],
            action="GRADCAM_GENERATED",
            status="SUCCESS",
            details=f"AI Attention Map generated for finding {finding}.",
        )

        return {
            "filename": file.filename,
            **result,
        }

    except ValueError as exc:
        log_event(
            username=user["username"],
            role=user["role"],
            action="GRADCAM_GENERATED",
            status="REJECTED",
            details=f"Invalid finding: {finding}.",
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except HTTPException:
        raise

    except Exception as exc:
        print("Grad-CAM error:", type(exc).__name__, repr(exc))

        log_event(
            username=user["username"],
            role=user["role"],
            action="GRADCAM_GENERATED",
            status="FAILED",
            details=f"Server error type: {type(exc).__name__}.",
        )

        raise HTTPException(
            status_code=500,
            detail="An error occurred while generating the AI attention map.",
        ) from exc


@app.get("/records")
def records(
    limit: int = Query(default=200, ge=1, le=1000),
    user=Depends(require_roles("ADMIN", "DOCTOR")),
):
    result = list_analysis_records(limit)

    log_event(
        username=user["username"],
        role=user["role"],
        action="RECORD_LIST_VIEW",
        status="SUCCESS",
        details=f"Viewed up to {limit} analysis records.",
    )

    return {"records": result}


@app.get("/records/{record_id}")
def record_detail(
    record_id: str,
    user=Depends(require_roles("ADMIN", "DOCTOR")),
):
    record = get_analysis_record(record_id)

    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")

    log_event(
        username=user["username"],
        role=user["role"],
        action="RECORD_VIEW",
        status="SUCCESS",
        details=f"Viewed analysis record {record_id}.",
    )

    return record


@app.get("/records/{record_id}/export")
def export_record(
    record_id: str,
    user=Depends(require_roles("ADMIN", "DOCTOR")),
):
    record = get_analysis_record(record_id)

    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")

    payload = json.dumps(record, indent=2, ensure_ascii=False).encode("utf-8")

    log_event(
        username=user["username"],
        role=user["role"],
        action="RECORD_EXPORT",
        status="SUCCESS",
        details=f"Exported analysis record {record_id}.",
    )

    return StreamingResponse(
        iter([payload]),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="analysis_record_{record_id}.json"'
            )
        },
    )


if FRONTEND_ASSETS.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_ASSETS)),
        name="assets",
    )


@app.get("/{full_path:path}")
async def serve_react(full_path: str):
    index_file = FRONTEND_DIST / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Frontend build was not found. "
                "Run 'npm run build' inside the frontend folder."
            ),
        )

    requested_file = FRONTEND_DIST / full_path

    if full_path and requested_file.exists() and requested_file.is_file():
        return FileResponse(requested_file)

    return FileResponse(index_file)
