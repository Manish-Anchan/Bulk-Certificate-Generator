#!/usr/bin/env python3
"""Interactive demonstration script for Bulk Certificate Generator API.

Simulates submitting a bulk certificate job, polling progress until completed,
verifying certificates, and downloading both single PDF and bulk ZIP archive.
"""

import sys
import time

import httpx

BASE_URL = "http://localhost:8000"


def run_demo():
    print("=" * 65)
    print("🎓 BULK CERTIFICATE GENERATOR - LIVE DEMO")
    print("=" * 65)

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Health check
        print("\n1️⃣ Checking API Health Status...")
        try:
            health = client.get("/health").json()
            print(f"   Status: {health['status']} | Version: {health['version']} | Env: {health['environment']}")
        except Exception:  # noqa: BLE001
            print(f"❌ Could not connect to API at {BASE_URL}. Is the server running?")
            print("   Run: uv run uvicorn app.main:app --port 8000")
            sys.exit(1)

        # 2. Submit Bulk Generation Request
        print("\n2️⃣ Submitting Bulk Certificate Request...")
        payload = {
            "event_name": "Senior Backend Engineering Summit 2026",
            "issuer_name": "International Software Architects Association",
            "certificate_title": "Certificate of Excellence",
            "issue_date": "2026-10-11",
            "recipients": [
                {"name": "Siddharth Rao", "email": "siddharth@example.com", "custom_fields": {"track": "System Design", "grade": "Distinction"}},
                {"name": "Ananya Sharma", "email": "ananya@example.com", "custom_fields": {"track": "Cloud Architecture", "grade": "Honors"}},
                {"name": "Vikram Malhotra", "email": "vikram@example.com", "custom_fields": {"track": "Distributed Systems", "grade": "Merit"}},
                {"name": "Priya Nambiar", "email": "priya@example.com", "custom_fields": {"track": "Reliability Engineering", "grade": "Distinction"}},
                {"name": "Arjun Patel", "email": "arjun@example.com", "custom_fields": {"track": "Performance Optimization", "grade": "High Honors"}},
            ],
        }

        resp = client.post("/api/v1/jobs", json=payload)
        if resp.status_code != 202:
            print(f"❌ Failed to submit job: {resp.status_code} {resp.text}")
            sys.exit(1)

        job_info = resp.json()
        job_id = job_info["job_id"]
        print("   ✅ Job Enqueued Successfully!")
        print(f"   Job ID: {job_id}")
        print(f"   Total Recipients: {job_info['total_recipients']}")
        print(f"   Status URL: {job_info['status_url']}")

        # 3. Poll for progress
        print("\n3️⃣ Polling Progress...")
        while True:
            status_data = client.get(f"/api/v1/jobs/{job_id}").json()
            status = status_data["status"]
            processed = status_data["processed_count"]
            total = status_data["total_recipients"]
            pct = status_data["progress_percentage"]
            print(f"   Status: {status} | Progress: {processed}/{total} ({pct}%)")

            if status in ["COMPLETED", "PARTIALLY_COMPLETED", "FAILED"]:
                break
            time.sleep(0.5)

        print("\n4️⃣ Job Finished!")
        print(f"   Successful: {status_data['success_count']}")
        print(f"   Failed:     {status_data['failed_count']}")

        # 5. Verify & Download first certificate
        first_recipient = status_data["recipients"][0]
        cert_id = first_recipient["certificate_id"]
        print(f"\n5️⃣ Inspecting Certificate for: {first_recipient['recipient_name']}")
        print(f"   Certificate ID: {cert_id}")

        # Verification check
        verify_data = client.get(f"/api/v1/certificates/{cert_id}/verify").json()
        print(f"   Verification: {verify_data['verification_message']} (Valid: {verify_data['valid']})")

        # Download individual PDF
        pdf_resp = client.get(f"/api/v1/certificates/{cert_id}/download")
        filename = f"{cert_id}.pdf"
        with open(filename, "wb") as f:
            f.write(pdf_resp.content)
        print(f"   📥 Downloaded single PDF: {filename} ({len(pdf_resp.content)} bytes)")

        # 6. Download ZIP
        zip_url = status_data["zip_download_url"]
        zip_resp = client.get(zip_url)
        zip_filename = f"certificates_{job_id}.zip"
        with open(zip_filename, "wb") as f:
            f.write(zip_resp.content)
        print(f"   📦 Downloaded bulk ZIP: {zip_filename} ({len(zip_resp.content)} bytes)")

        print("\n" + "=" * 65)
        print("🎉 Live Demo Completed Successfully!")
        print("=" * 65)


if __name__ == "__main__":
    run_demo()
