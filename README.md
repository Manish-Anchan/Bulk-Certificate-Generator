# 🎓 Bulk Certificate Generator Backend

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

A production-grade, asynchronous backend API built with **FastAPI** to accept bulk certificate generation requests, validate recipient data, dynamically render styled vector PDF certificates from a predefined template, track execution progress in real time with granular fault isolation, and provide flexible retrieval (individual PDF download or bulk `.zip` archive).

---

## 🌟 Key Features

- **Bulk Processing**: Designed specifically around handling batch generation of certificates without HTTP timeouts using the Asynchronous Job Pattern (`202 Accepted` + progress polling).
- **Fault Isolation**: An individual recipient with malformed data or a generation error will **never** stop other valid certificates from being generated.
- **Real-Time Progress Tracking**: Granular counters (`total`, `processed`, `successful`, `failed`) and status transitions (`PENDING`, `PROCESSING`, `COMPLETED`, `PARTIALLY_COMPLETED`).
- **Crisp Vector Certificates**: High-fidelity PDF certificates rendered with ReportLab (pure Python, vector graphics, dynamic typography, and unique verification QR code).
- **Dual Retrieval & Verification**:
  - Individual PDF streaming (`GET /api/v1/certificates/{id}/download`)
  - Batch `.zip` archive export (`GET /api/v1/jobs/{id}/download`)
  - Public verification endpoint (`GET /api/v1/certificates/{id}/verify`)
- **Dual Database Support**: SQLite (WAL mode) out of the box for zero-setup evaluation, plus PostgreSQL support for production deployments.

---

## 🚀 Quick Start

### Option 1: Using `uv` (Recommended - Blazing Fast)

```bash
# Clone the repository
git clone <repo-url>
cd bulk-certificate-generator

# Create virtual environment and install dependencies
uv sync

# Run the API server
uv run uvicorn app.main:app --reload --port 8000
```

### Option 2: Using standard `pip`

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn app.main:app --reload --port 8000
```

---

## 📖 Interactive API Documentation

Once the server is running, navigate to:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🧪 Running Tests

```bash
# Using uv
uv run pytest -v

# Using standard pytest
pytest -v
```

---

## 📂 Project Architecture

```text
bulk-certificate-generator/
├── app/
│   ├── main.py                     # Application factory & lifespan
│   ├── core/
│   │   ├── config.py               # Pydantic BaseSettings & env configuration
│   │   ├── database.py             # SQLAlchemy 2.0 async engine & session maker
│   │   └── logging.py              # Structured application logger
│   ├── models/                     # SQLAlchemy ORM models (Job, Recipient)
│   ├── schemas/                    # Pydantic v2 validation models
│   ├── services/                   # Business logic (PDF generator, job worker, storage)
│   └── api/
│       └── v1/                     # REST API endpoints (jobs, certificates)
├── storage/                        # Stored PDF certificates & archives
├── tests/                          # Comprehensive pytest test suite
├── pyproject.toml                  # Project metadata & uv dependencies
├── requirements.txt                # Production requirements (pip compatible)
├── requirements-dev.txt            # Development/testing requirements
└── README.md
```
