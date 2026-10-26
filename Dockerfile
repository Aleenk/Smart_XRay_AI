# ---------- Build React frontend ----------
FROM node:24-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ---------- Python / FastAPI backend ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements-cloud.txt ./

RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements-cloud.txt

COPY backend ./backend

# React build generated in the first stage.
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

EXPOSE 8080

# Cloud Run injects PORT. Fall back to 8080 for local Docker runs.
CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
