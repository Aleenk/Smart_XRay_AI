# Smart X-Ray AI

Smart X-Ray AI is an educational AI-assisted chest X-ray analysis system developed as a final Software Engineering project.

The application allows an authorized user to upload a chest X-ray image, receive AI-assisted screening for selected radiological findings, review model confidence scores, and request a Grad-CAM **AI Attention Map** that highlights image regions that influenced the model.

> **Medical safety notice:** Smart X-Ray AI is an educational decision-support prototype. It does **not** provide a medical diagnosis, does not replace a radiologist or physician, and is not intended for clinical use.

## Public Application

Cloud deployment:

**https://smart-xray-ai-717746889062.me-west1.run.app**

Source repository:

**https://github.com/Aleenk/Smart_XRay_AI**

---

## Supported Findings

The patient-facing application evaluates four selected chest findings:

- Pneumonia
- Pneumothorax
- Pleural Effusion
- Cardiomegaly

The model is multi-label, so more than one supported finding may be flagged for the same image.

If none of the four supported findings crosses its validation-derived threshold, the application reports:

**No selected finding detected**

This message is not equivalent to a medical statement that the X-ray is normal.

---

## Main Features

### AI Analysis

- PNG/JPEG chest X-ray upload
- DenseNet121-based multi-label inference
- Validation-derived decision threshold for each supported finding
- Multiple findings can be returned for a single image
- Patient-friendly result presentation
- Educational explanation for each supported finding
- Optional Grad-CAM AI Attention Map
- Medical safety messaging

### Authentication and Access Control

- Username/password authentication
- Bearer-token sessions
- Session expiration
- Logout and session revocation
- Password hashing with PBKDF2-HMAC-SHA256 and random salts
- Role-Based Access Control enforced by the FastAPI backend

Three default roles are implemented:

| Role | Analysis | Grad-CAM | View / Export Records | User Administration | Audit Trail |
|---|---:|---:|---:|---:|---:|
| ADMIN | Yes | Yes | Yes | Yes | Yes |
| DOCTOR | Yes | Yes | Yes | No | No |
| TECHNICIAN | Yes | Yes | No | No | No |

The frontend hides unauthorized sections, while the backend independently enforces permissions and returns HTTP `403 Forbidden` for unauthorized access attempts.

### Electronic Records

For each successful analysis, the system can store an electronic analysis record containing:

- Record ID
- Timestamp
- Username
- User role
- SHA-256 digest of the uploaded image
- Image content type
- Detected findings
- Model scores
- Whether no selected finding was detected

The uploaded image bytes are **not** stored in the records database.

Authorized ADMIN and DOCTOR users can export an individual analysis record as JSON.

### Audit Trail

The security layer maintains a time-stamped Audit Trail for important application and security events.

Each audit entry contains a SHA-256 hash linked to the previous entry. The system can verify the chain and detect modification of a logged entry.

ADMIN users can:

- View the Audit Trail
- Verify the audit hash chain
- Export the Audit Trail as CSV

---

## Academic Part 11 / HIPAA-Oriented Safeguards

Smart X-Ray AI includes an **academic implementation of controls inspired by electronic-record, access-control, audit, and privacy requirements** discussed in the course.

Implemented safeguards include:

- Individual user accounts
- Role-based access restrictions
- Password hashing
- Expiring and revocable sessions
- Time-stamped Audit Trail
- SHA-256 audit integrity chain
- Electronic analysis records
- Record export
- Audit export
- Account activation/deactivation
- Backend enforcement of authorization
- HTTPS on the public Cloud Run deployment
- Cloud passwords stored through Google Secret Manager rather than committed to source code
- No patient name, address, date of birth, or other patient identity field is required by the application
- Uploaded image bytes are not saved in the application records database

> **Compliance limitation:** This project is **not** represented as FDA 21 CFR Part 11 certified, HIPAA compliant, clinically validated, or approved for regulated medical use. It is an academic prototype demonstrating selected safeguards and concepts.

---

## Model

The final model uses:

- **Architecture:** DenseNet121
- **Framework:** PyTorch
- **Approach:** Transfer learning
- **Task:** Multi-label chest X-ray classification
- **Input:** 224 × 224 pixels, 3 channels
- **Final checkpoint:** Epoch 5
- **Validation disease Macro AUC:** approximately 0.8441
- **Final test disease Macro AUC:** approximately 0.8507

The model was trained using the NIH ChestX-ray14 dataset.

Dataset summary:

- Total images: 112,120
- Total patients: 30,805
- Train: 78,566 images
- Validation: 16,106 images
- Test: 17,448 images

Patient-level splitting was used to reduce leakage between training, validation, and test sets.

### Training Outputs

The training pipeline used five outputs:

- Pneumonia
- Pneumothorax
- Effusion
- Cardiomegaly
- No Finding

The patient-facing application presents the four selected disease findings. The message **No selected finding detected** is derived from the four disease thresholds and should not be interpreted as a confirmed normal study.

---

## Validation Thresholds

| Finding | Threshold |
|---|---:|
| Pneumonia | 0.0957 |
| Pneumothorax | 0.0915 |
| Effusion | 0.2630 |
| Cardiomegaly | 0.0492 |

The threshold file is stored at:

```text
backend/model/thresholds.json
```

---

## Final Test Results

| Finding | AUC | Recall | Specificity | Precision | F1 |
|---|---:|---:|---:|---:|---:|
| Pneumonia | 0.7368 | 0.6905 | 0.6652 | 0.0245 | 0.0473 |
| Pneumothorax | 0.8774 | 0.8778 | 0.7041 | 0.1298 | 0.2261 |
| Effusion | 0.8763 | 0.8307 | 0.7730 | 0.3261 | 0.4684 |
| Cardiomegaly | 0.9123 | 0.8387 | 0.8369 | 0.1308 | 0.2263 |

Overall disease Macro AUC:

```text
0.8507
```

No Finding AUC:

```text
0.7705
```

Some selected findings are relatively rare in the dataset. As a result, precision can be low even when AUC and recall are stronger. For this reason, the interface uses cautious wording such as **Possible finding(s) detected** rather than presenting model output as a confirmed diagnosis.

---

## Grad-CAM Explainability

Smart X-Ray AI uses Grad-CAM to generate an **AI Attention Map** for a selected finding.

The heatmap indicates image regions that influenced the model output. It does not prove that a disease is anatomically located in a highlighted region and must not be interpreted as a radiological localization result.

---

## Architecture

```text
Authorized User
      |
      v
React Frontend
      |
      | Bearer session token
      v
FastAPI Backend
      |
      +--------------------+
      |                    |
      v                    v
Security Layer          AI Pipeline
      |                    |
      |                    v
      |             Image preprocessing
      |                    |
      |                    v
      |               DenseNet121
      |                    |
      |              +-----+------+
      |              |            |
      |              v            v
      |          Prediction    Grad-CAM
      |
      +--> SQLite
           - users
           - sessions
           - audit_log
           - analysis_records
```

---

## Project Structure

```text
Smart_XRay_AI/
|
├── backend/
│   ├── main.py
│   ├── security.py
│   ├── model/
│   │   ├── inference.py
│   │   ├── best_final_model.pth
│   │   └── thresholds.json
│   ├── utils/
│   │   └── image_utils.py
│   └── data/
│       └── smart_xray.db
|
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── AuthGate.jsx
│   │   ├── AuthGate.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   └── package-lock.json
|
├── Dockerfile
├── requirements.txt
├── requirements-cloud.txt
└── README.md
```

---

## Main API Endpoints

### Public

```text
GET /health
POST /auth/login
```

### Authenticated

```text
POST /auth/logout
GET  /auth/me
POST /predict
POST /gradcam
```

### ADMIN

```text
GET   /admin/users
POST  /admin/users
PATCH /admin/users/{user_id}/active

GET /audit
GET /audit/verify
GET /audit/export
```

### ADMIN or DOCTOR

```text
GET /records
GET /records/{record_id}
GET /records/{record_id}/export
```

---

## Local Setup

### Requirements

- Python 3.12 recommended
- Node.js / npm
- Model checkpoint and threshold file under `backend/model/`

### 1. Create the Python environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure local account passwords

Set the three environment variables **before the first startup that creates the local database**:

```powershell
$env:SMART_XRAY_ADMIN_PASSWORD="<your-admin-password>"
$env:SMART_XRAY_DOCTOR_PASSWORD="<your-doctor-password>"
$env:SMART_XRAY_TECHNICIAN_PASSWORD="<your-technician-password>"
```

Default usernames:

```text
admin
doctor
technician
```

Do not commit real passwords to GitHub.

> If the local database was already initialized, changing these environment variables does not automatically replace the password hashes of existing users.

### 3. Build the React frontend

```powershell
cd frontend
npm install
npm run build
cd ..
```

### 4. Start FastAPI

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

## Database

The security layer uses SQLite.

Local default:

```text
backend/data/smart_xray.db
```

On Google Cloud Run:

```text
/tmp/smart_xray.db
```

Tables:

- `users`
- `sessions`
- `audit_log`
- `analysis_records`

### Important Cloud Limitation

Cloud Run's writable local filesystem is ephemeral. Therefore the current SQLite database under `/tmp` is suitable for an academic demonstration but **not** for durable regulated records.

A new Cloud Run instance, restart, or revision may result in a fresh local database. A production-grade system would require a persistent managed database and appropriate backup, retention, access-control, monitoring, and regulatory processes.

---

## Security Configuration

### Password Storage

The current implementation uses:

- PBKDF2-HMAC-SHA256
- Random 16-byte salt
- 260,000 iterations

### Sessions

- Random bearer token
- SHA-256 token digest stored in the database
- Default lifetime: 8 hours
- Logout revokes the session

The lifetime can be changed with:

```text
SMART_XRAY_SESSION_HOURS
```

### Cloud Secrets

The Cloud Run deployment reads account passwords from Google Secret Manager.

Environment-variable mappings:

```text
SMART_XRAY_ADMIN_PASSWORD
    -> smart-xray-admin-password

SMART_XRAY_DOCTOR_PASSWORD
    -> smart-xray-doctor-password

SMART_XRAY_TECHNICIAN_PASSWORD
    -> smart-xray-technician-password
```

The Cloud Run revision service account requires the **Secret Manager Secret Accessor** IAM role for the referenced secrets.

---

## Cloud Deployment

The repository includes a multi-stage Dockerfile:

1. Node 24 Alpine builds the React frontend.
2. Python 3.12 slim installs the backend dependencies.
3. The React production build is copied into the final FastAPI container.
4. Uvicorn listens on the Cloud Run `PORT`.

Region:

```text
me-west1
```

Public URL:

**https://smart-xray-ai-717746889062.me-west1.run.app**

---

## Production Dependency Versions

| Component | Version |
|---|---|
| Python base image | 3.12-slim |
| Node build image | 24-alpine |
| FastAPI | 0.157.0 |
| Uvicorn | 0.54.0 |
| Pillow | 13.0.0 |
| NumPy | 2.5.4 |
| PyTorch CPU | 2.14.1+cpu |
| Torchvision CPU | 0.29.1+cpu |
| React | ^19.3.1 |
| React DOM | ^19.3.1 |
| Vite | ^8.3.4 |

Some packages, such as `python-multipart`, are currently not version-pinned in `requirements-cloud.txt`.

---

## Privacy and Data Handling

The application does not require the user to enter patient identity information.

For analysis records, the current implementation stores a SHA-256 digest of the uploaded image instead of storing the uploaded image bytes in the SQLite records database.

This design reduces stored data but does **not** by itself make the application suitable for processing real protected health information.

Do not use identifiable clinical data with this academic prototype.

---

## Known Limitations

- Educational prototype only
- Not a medical device
- Not clinically validated
- Not FDA 21 CFR Part 11 certified
- Not formally HIPAA compliant
- Low precision for some rare findings
- Grad-CAM indicates model attention, not confirmed disease localization
- Current Cloud Run SQLite storage is ephemeral
- No production-grade persistent clinical database
- No formal electronic-signature workflow
- No hospital identity provider integration
- No formal regulatory validation package

---

## Authors

Final project developed by:

- **aleen alasd**
- **Shayma Nabbari**

Instructor:

- **Shay Ginzburg**

---

## Disclaimer

Smart X-Ray AI is an educational decision-support prototype created as an academic project. It does not provide a diagnosis, treatment recommendation, or clinical clearance. Model outputs and attention maps must not be used as a substitute for professional medical evaluation.
