# Smart X-Ray AI

Smart X-Ray AI is an educational AI-assisted chest X-ray analysis system developed as a final project.

The system allows a user to upload a chest X-ray image and receive AI-assisted screening for selected chest findings. It also provides short educational explanations and an AI Attention Map based on Grad-CAM.

> **Important:** Smart X-Ray AI is an educational decision-support prototype. It does not provide a medical diagnosis and does not replace professional medical evaluation.

---

## Supported Findings

The model analyzes chest X-rays for the following findings:

- Pneumonia
- Pneumothorax
- Pleural Effusion
- Cardiomegaly

The model was trained as a multi-label classifier, so more than one finding may be flagged in the same image.

---

## Main Features

- Upload chest X-ray images in PNG or JPEG format
- AI-assisted analysis using DenseNet121
- Multi-label prediction for four supported findings
- Validation-based decision thresholds for each finding
- Patient-friendly result presentation
- Short medical + engineering explanation of how a finding was identified
- Grad-CAM AI Attention Map for explainability
- Educational information for each supported finding
- Medical disclaimer and safety messaging
- FastAPI backend
- React frontend

---

## Model

The final model uses:

- **Architecture:** DenseNet121
- **Framework:** PyTorch
- **Approach:** Transfer learning
- **Task:** Multi-label chest X-ray classification
- **Input size:** 224 x 224
- **Final checkpoint:** Epoch 5
- **Validation Disease Macro AUC:** approximately 0.8441
- **Final Test Disease Macro AUC:** approximately 0.8507

The model was trained on the NIH ChestX-ray14 dataset.

The dataset contains 112,120 chest X-ray images from 30,805 patients.

Patient-level splitting was used to reduce data leakage between train, validation, and test sets.

Dataset split:

- Train: 78,566 images
- Validation: 16,106 images
- Test: 17,448 images

---

## Validation Thresholds

Decision thresholds were selected using the validation set and were not tuned on the test set.

| Finding | Threshold |
|---|---:|
| Pneumonia | 0.0957 |
| Pneumothorax | 0.0915 |
| Effusion | 0.2630 |
| Cardiomegaly | 0.0492 |

The thresholds are stored in:

```text
backend/model/thresholds.json
```

These values are used internally by the backend. They are not shown to the patient in the final interface.

---

## Final Test Results

| Finding | AUC | Recall | Specificity | Precision | F1 |
|---|---:|---:|---:|---:|---:|
| Pneumonia | 0.7368 | 0.6905 | 0.6652 | 0.0245 | 0.0473 |
| Pneumothorax | 0.8774 | 0.8778 | 0.7041 | 0.1298 | 0.2261 |
| Effusion | 0.8763 | 0.8307 | 0.7730 | 0.3261 | 0.4684 |
| Cardiomegaly | 0.9123 | 0.8387 | 0.8369 | 0.1308 | 0.2263 |

Overall Disease Macro AUC on the final test set:

```text
0.8507
```

No Finding AUC:

```text
0.7705
```

Because some findings are relatively rare in the dataset, precision can be low even when recall and AUC are reasonable. For this reason, the application presents results as **possible findings for medical review**, not as confirmed diagnoses.

---

## Explainability with Grad-CAM

Smart X-Ray AI includes Grad-CAM to provide an AI Attention Map.

The attention map highlights image regions that had a stronger influence on the model's prediction.

It is important to understand that the highlighted regions:

- show model attention/influence
- do not prove that disease is located in the highlighted area
- do not replace radiological interpretation

The frontend displays the Grad-CAM map only when the user requests it.

---

## Project Structure

```text
Smart_XRay_AI/
│
├── backend/
│   ├── main.py
│   │
│   ├── model/
│   │   ├── inference.py
│   │   ├── best_final_model.pth
│   │   └── thresholds.json
│   │
│   └── utils/
│       └── image_utils.py
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── index.css
│   │
│   ├── package.json
│   └── ...
│
├── requirements.txt
└── README.md
```

---

## Backend Setup

### 1. Create and activate a Python virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```powershell
pip install -r requirements.txt
```

### 3. Start the FastAPI backend

From the project root:

```powershell
uvicorn backend.main:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

FastAPI Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

## Frontend Setup

Node.js and npm are required.

### 1. Open the frontend directory

```powershell
cd frontend
```

### 2. Install frontend dependencies

```powershell
npm install
```

### 3. Start the React development server

```powershell
npm run dev
```

The frontend will normally run at:

```text
http://localhost:5173
```

---

## API Endpoints

### `GET /`

Checks whether the backend is running.

### `GET /health`

Returns backend health and model information.

### `POST /predict`

Accepts a PNG/JPEG chest X-ray and returns AI-assisted findings.

### `POST /gradcam`

Accepts a chest X-ray and a finding name and returns a Grad-CAM AI Attention Map.

Supported finding names:

```text
Pneumonia
Pneumothorax
Effusion
Cardiomegaly
```

---

## Typical System Flow

```text
User uploads chest X-ray
        ↓
React frontend
        ↓
FastAPI backend
        ↓
Image preprocessing
        ↓
DenseNet121 final model
        ↓
Multi-label prediction
        ↓
Validation thresholds
        ↓
Possible finding(s)
        ↓
Medical + engineering explanation
        ↓
Optional Grad-CAM AI Attention Map
```

---

## Medical Safety

The system is designed for educational and research purposes only.

It must not be used as a substitute for a doctor, radiologist, emergency service, or clinical diagnostic system.

A result such as "Possible finding detected" means that the model identified image patterns associated with that finding according to its learned representation and decision criteria. It does **not** confirm that the patient has the condition.

If a user has severe symptoms such as significant chest pain, severe breathing difficulty, fainting, confusion, or other urgent symptoms, they should seek appropriate medical care regardless of the AI result.

---

## Technologies

### AI / Machine Learning

- Python
- PyTorch
- Torchvision
- DenseNet121
- NumPy
- Pandas
- scikit-learn
- Matplotlib
- Grad-CAM

### Backend

- FastAPI
- Uvicorn
- Pillow
- python-multipart

### Frontend

- React
- Vite
- JavaScript
- CSS

---

## Authors

Final project developed by:

- Aleen alasd
- Shaima Nabari

Instructor: Shay Ginzburg

---

## Disclaimer

Smart X-Ray AI is an educational decision-support prototype created as an academic project. It does not provide medical diagnosis, treatment recommendations, or clinical clearance.
