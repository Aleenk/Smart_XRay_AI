from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.utils.image_utils import prepare_xray_image
from backend.model.inference import predict_xray, generate_gradcam


app = FastAPI(
    title="Smart X-Ray AI",
    description="AI-assisted chest X-ray analysis prototype",
    version="1.0.0",
)


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Smart X-Ray AI"
    }


# ---------------------------------------------------------
# AI PREDICTION
# ---------------------------------------------------------

@app.post("/predict")
async def predict(
    file: UploadFile = File(...)
):
    try:

        if file.content_type not in [
            "image/png",
            "image/jpeg",
            "image/jpg",
        ]:
            raise HTTPException(
                status_code=400,
                detail="Only PNG and JPEG images are supported."
            )

        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty."
            )

        image_data = prepare_xray_image(
            file_bytes
        )

        image = image_data["image"]

        result = predict_xray(
            image
        )

        return {
            "filename": file.filename,
            **result
        }

    except HTTPException:
        raise

    except Exception as exc:

        print(
            "Prediction error:",
            type(exc).__name__,
            repr(exc)
        )

        raise HTTPException(
            status_code=500,
            detail="An error occurred while analyzing the X-ray."
        )


# ---------------------------------------------------------
# GRAD-CAM
# ---------------------------------------------------------

@app.post("/gradcam")
async def gradcam(
    file: UploadFile = File(...),
    finding: str = Form(...)
):
    try:

        if file.content_type not in [
            "image/png",
            "image/jpeg",
            "image/jpg",
        ]:
            raise HTTPException(
                status_code=400,
                detail="Only PNG and JPEG images are supported."
            )

        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty."
            )

        image_data = prepare_xray_image(
            file_bytes
        )

        image = image_data["image"]

        result = generate_gradcam(
            image,
            finding
        )

        return {
            "filename": file.filename,
            **result
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except HTTPException:
        raise

    except Exception as exc:

        print(
            "Grad-CAM error:",
            type(exc).__name__,
            repr(exc)
        )

        raise HTTPException(
            status_code=500,
            detail="An error occurred while generating the AI attention map."
        )


# ---------------------------------------------------------
# REACT STATIC FILES
# ---------------------------------------------------------

if FRONTEND_ASSETS.exists():

    app.mount(
        "/assets",
        StaticFiles(
            directory=str(FRONTEND_ASSETS)
        ),
        name="assets"
    )


# ---------------------------------------------------------
# REACT FRONTEND
# Keep this LAST.
# ---------------------------------------------------------

@app.get("/{full_path:path}")
async def serve_react(full_path: str):

    index_file = FRONTEND_DIST / "index.html"

    if not index_file.exists():

        raise HTTPException(
            status_code=503,
            detail=(
                "Frontend build was not found. "
                "Run 'npm run build' inside the frontend folder."
            )
        )

    requested_file = FRONTEND_DIST / full_path

    if (
        full_path
        and requested_file.exists()
        and requested_file.is_file()
    ):
        return FileResponse(
            requested_file
        )

    return FileResponse(
        index_file
    )