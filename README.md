# 🎓 Bulk Certificate Generator Backend

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-46E3B7.svg?logo=render&logoColor=white)](https://bulk-certificate-generator-bwvb.onrender.com/)
[![Database](https://img.shields.io/badge/Database-Neon%20PostgreSQL-00e599.svg?logo=postgresql&logoColor=white)](https://neon.tech/)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests](https://img.shields.io/badge/tests-18%20passed-success.svg)](https://docs.pytest.org/)

A production-grade, asynchronous backend API built with **FastAPI** designed to handle bulk certificate generation with high throughput, strict per-recipient fault isolation, real-time progress polling, and flexible retrieval (single vector PDF or bulk `.zip` archive).

> [!TIP]
> ### 🌐 Live Cloud Deployment
> The application is deployed live with a managed **Neon PostgreSQL** database:
> - **Interactive Web Dashboard**: [https://bulk-certificate-generator-bwvb.onrender.com/](https://bulk-certificate-generator-bwvb.onrender.com/)
> - **Interactive Swagger Docs**: [https://bulk-certificate-generator-bwvb.onrender.com/docs](https://bulk-certificate-generator-bwvb.onrender.com/docs)
> - **ReDoc Documentation**: [https://bulk-certificate-generator-bwvb.onrender.com/redoc](https://bulk-certificate-generator-bwvb.onrender.com/redoc)
> - **API Health Check**: [https://bulk-certificate-generator-bwvb.onrender.com/health](https://bulk-certificate-generator-bwvb.onrender.com/health)


---

## 📋 Table of Contents
1. [Architecture & System Flow](#-architecture--system-flow)
2. [Key Engineering & Design Decisions](#-key-engineering--design-decisions)
3. [Setup & Quick Start](#-setup--quick-start)
   - [Option A: Using `uv` (Recommended)](#option-a-using-uv-recommended)
   - [Option B: Using standard `pip`](#option-b-using-standard-pip)
   - [Option C: Using Docker Compose](#option-c-using-docker-compose)
4. [Running the Test Suite](#-running-the-test-suite)
5. [API Specification & cURL Examples](#-api-specification--curl-examples)
   - [1. Submit Certificate Job (POST /api/v1/jobs)](#1-submit-bulk-generation-request)
   - [2. Poll Job Progress (GET /api/v1/jobs/{id})](#2-check-job-status--progress)
   - [3. Download Individual Certificate (GET /api/v1/certificates/{id}/download)](#3-download-individual-certificate-pdf)
   - [4. Download All Certificates as ZIP (GET /api/v1/jobs/{id}/download)](#4-download-all-certificates-as-zip)
   - [5. Public Certificate Verification (GET /api/v1/certificates/{id}/verify)](#5-public-certificate-verification)
6. [Live Interactive Demo](#-live-interactive-demo)
7. [Production Scaling Considerations](#-production-scaling-considerations)

---

## 🏛 Architecture & System Flow

```
[ Client / Webhook ]
        │
        │ 1. POST /api/v1/jobs (Bulk JSON of recipients)
        ▼
[ FastAPI Ingestion Layer ] ──> Validates schema & batch constraints (1-5000)
        │
        ├──> Creates Job & Recipient records in DB (status: PENDING)
        ├──> Enqueues background generation task
        └──> Returns 202 Accepted (job_id, status_url) immediately (10ms)
        │
        ▼ (Asynchronous Execution)
[ Background Worker (ThreadPoolExecutor) ]
        │
        ├──> Iterates through recipients
        ├──> Isolates each generation in a dedicated try/except boundary
        ├──> Dynamic Vector PDF rendering via ReportLab (~15ms per PDF)
        ├──> Embedded Verification QR code stamped onto PDF
        ├──> Saves PDF to storage directory
        └──> Updates DB: increments processed, success, or failed counters
        │
        ▼
[ Final Job State: COMPLETED / PARTIALLY_COMPLETED / FAILED ]
        │
        ├──> GET /api/v1/jobs/{id}                 (Real-time progress polling)
        ├──> GET /api/v1/certificates/{id}/download (Single PDF streaming)
        ├──> GET /api/v1/jobs/{id}/download         (Bulk ZIP archive streaming)
        └──> GET /api/v1/certificates/{id}/verify   (Public authenticity verification)
```

---

## 💡 Key Engineering & Design Decisions

### 1. Synchronous vs. Asynchronous Background Processing
- **Problem**: Generating certificates for 100 to 5,000 recipients involves rendering PDFs and writing them to storage. Doing this synchronously inside an HTTP request will trigger browser/proxy gateway timeouts (e.g., 30s Nginx timeout), tie up server threads, and crash under load.
- **Solution**: We implement the **Asynchronous Job Pattern**:
  - The client submits the batch and receives `HTTP 202 Accepted` within milliseconds with a unique `job_id` and status polling URL.
  - Generation occurs in the background, updating progress counters (`total`, `processed`, `success`, `failed`).
  - The client polls `GET /api/v1/jobs/{job_id}` to display a real-time progress bar.

### 2. Offloading CPU-Bound PDF Rendering via ThreadPoolExecutor
- PDF compilation with ReportLab is CPU-bound. If executed on the main asyncio event loop, it would block asynchronous I/O handling for other API requests.
- We offload rendering calls using `asyncio.get_running_loop().run_in_executor(thread_pool, ...)` to a dedicated `ThreadPoolExecutor`. This maintains high event loop responsiveness.

### 3. Strict Fault Isolation (Zero Cascading Failures)
- A single corrupted recipient record (e.g. invalid formatting, disk error) will **never** abort the batch.
- Each recipient is isolated in an atomic `try...except` block:
  - Valid recipients are generated and marked `SUCCESS`.
  - Faulty recipients are marked `FAILED` with the exact error message preserved in the database.
  - Final status transitions to `PARTIALLY_COMPLETED` (or `COMPLETED` if all succeed, or `FAILED` if all fail).

### 4. Vector PDF Rendering via ReportLab
- We chose **ReportLab** over headless browser solutions (such as WeasyPrint or Puppeteer):
  - **Zero Heavy C-Dependencies**: Pure Python, installs cleanly everywhere without requiring Chrome, WebKit, or system font libraries.
  - **Blazing Fast**: Generates a certificate in ~15 milliseconds (~3.4 KB per certificate).
  - **True Vector Output**: Razor-sharp typography and geometric vector borders at any print scale.
  - **Dynamic Scaling**: Automatically adjusts font sizes for long names to prevent text overflow.

### 5. Dual-Mode Database Architecture
- **Evaluation Mode (SQLite with WAL mode)**: Runs instantly without installing or configuring external services (`aiosqlite`).
- **Production Mode (PostgreSQL)**: Supported out of the box via `asyncpg` and SQLAlchemy 2.0 async engine in `docker-compose.yml`.

---

## 🚀 Setup & Quick Start

### Option A: Using `uv` (Recommended)

```bash
# 1. Clone repository and navigate to folder
git clone https://github.com/Manish-Anchan/Bulk-Certificate-Generator.git
cd Bulk-Certificate-Generator


# 2. Sync dependencies and create virtual environment
uv sync --extra dev

# 3. Launch application server
uv run uvicorn app.main:app --reload --port 8000
```

### Option B: Using standard `pip`

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Launch application server
uvicorn app.main:app --reload --port 8000
```

### Option C: Using Docker Compose

```bash
docker compose up --build
```

The server is available at:
- **Interactive Web Dashboard (Live UI)**: [http://localhost:8000/](http://localhost:8000)
- **Interactive Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)


---

## 🧪 Running the Test Suite

The test suite covers 100% of the minimum requirements specified in the assignment:
1. Creating a generation job
2. Input validation
3. Certificate generation
4. Job status & progress tracking
5. Handling individual certificate failure (fault isolation)
6. Retrieving generated certificates (individual PDF & bulk ZIP)

```bash
# Run tests with uv
uv run pytest -v

# Run tests with coverage
uv run pytest -v --cov=app

# Run linter & code quality checks
uv run ruff check .
```

---

## 📡 API Specification & cURL Examples

### 1. Submit Bulk Generation Request
**Endpoint:** `POST /api/v1/jobs`  
**Status Code:** `202 Accepted`

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
     -H "Content-Type: application/json" \
     -d '{
       "event_name": "Full Stack Mastery 2026",
       "issuer_name": "Tech Academy",
       "certificate_title": "Certificate of Completion",
       "issue_date": "2026-10-11",
       "recipients": [
         {
           "name": "Alice Johnson",
           "email": "alice@example.com",
           "custom_fields": {"grade": "A+", "hours": 40}
         },
         {
           "name": "Bob Smith",
           "email": "bob@example.com"
         }
       ]
     }'
```

**Response (`202 Accepted`):**
```json
{
  "job_id": "9d1830e1-7e83-4ce2-b132-7fd16527b14d",
  "status": "PENDING",
  "total_recipients": 2,
  "message": "Certificate generation job accepted and enqueued.",
  "status_url": "/api/v1/jobs/9d1830e1-7e83-4ce2-b132-7fd16527b14d"
}
```

---

### 2. Check Job Status & Progress
**Endpoint:** `GET /api/v1/jobs/{job_id}`  
**Query Params:** `limit=50&offset=0&status_filter=ALL`  
**Status Code:** `200 OK`

```bash
curl -X GET "http://localhost:8000/api/v1/jobs/9d1830e1-7e83-4ce2-b132-7fd16527b14d"
```

**Response (`200 OK`):**
```json
{
  "job_id": "9d1830e1-7e83-4ce2-b132-7fd16527b14d",
  "event_name": "Full Stack Mastery 2026",
  "issuer_name": "Tech Academy",
  "certificate_title": "Certificate of Completion",
  "issue_date": "2026-10-11",
  "status": "COMPLETED",
  "total_recipients": 2,
  "processed_count": 2,
  "success_count": 2,
  "failed_count": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-11T10:14:00Z",
  "completed_at": "2026-10-11T10:14:01Z",
  "zip_download_url": "/api/v1/jobs/9d1830e1-7e83-4ce2-b132-7fd16527b14d/download",
  "recipients": [
    {
      "id": "e6a2b378-...",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "status": "SUCCESS",
      "certificate_id": "CERT-2026-7A1B2C3D",
      "download_url": "/api/v1/certificates/CERT-2026-7A1B2C3D/download",
      "error_message": null,
      "generated_at": "2026-10-11T10:14:01Z"
    }
  ]
}
```

---

### 3. Download Individual Certificate PDF
**Endpoint:** `GET /api/v1/certificates/{certificate_id}/download`  
**Status Code:** `200 OK` (Streams binary PDF)

```bash
curl -O -J "http://localhost:8000/api/v1/certificates/CERT-2026-7A1B2C3D/download"
```

---

### 4. Download All Certificates as ZIP
**Endpoint:** `GET /api/v1/jobs/{job_id}/download`  
**Status Code:** `200 OK` (Streams compressed ZIP archive)

```bash
curl -O -J "http://localhost:8000/api/v1/jobs/9d1830e1-7e83-4ce2-b132-7fd16527b14d/download"
```

---

### 5. Public Certificate Verification
**Endpoint:** `GET /api/v1/certificates/{certificate_id}/verify`  
**Status Code:** `200 OK`

```bash
curl -X GET "http://localhost:8000/api/v1/certificates/CERT-2026-7A1B2C3D/verify"
```

**Response (`200 OK`):**
```json
{
  "valid": true,
  "certificate_id": "CERT-2026-7A1B2C3D",
  "recipient_name": "Alice Johnson",
  "event_name": "Full Stack Mastery 2026",
  "issuer_name": "Tech Academy",
  "certificate_title": "Certificate of Completion",
  "issue_date": "2026-10-11",
  "issued_at": "2026-10-11T10:14:01Z",
  "verification_message": "Certificate is authentic and officially recognized."
}
```

---

## 🎬 Live Interactive Demo

With the server running, execute the interactive CLI demo:

```bash
uv run python scripts/demo_bulk_run.py
```

This will automatically submit a batch, poll progress, verify a credential, and download both the individual certificate PDF and the aggregated ZIP archive.

---

## 🚀 Production Scaling Considerations

For enterprise workloads handling hundreds of thousands of certificates concurrently:

- **Distributed Task Queue**: Decouple worker processing from the API layer using **Celery** or **ARQ** with a **Redis** or **RabbitMQ** message broker to distribute generation across a fleet of worker pods.
- **Cloud Object Storage**: Transition from local disk storage to **AWS S3** or **Google Cloud Storage**, leveraging pre-signed URLs for direct streaming and reduced server bandwidth.
- **Batch Chunking & Parallel Dispatch**: Partition large recipient batches into chunks of 500 records to optimize database transactions, prevent memory spikes, and parallelize rendering workers across CPU cores.
- **Dedicated Rendering Microservice**: In very high-throughput systems, isolate PDF vector rendering into a specialized worker service with autoscaling based on queue depth.

