from datetime import date
from pathlib import Path

from app.services.certificate_generator import certificate_generator


def test_pdf_generation_magic_bytes(tmp_path: Path):
    """Test that generated PDF contains valid PDF magic header and content."""
    pdf_path = tmp_path / "cert_test.pdf"

    pdf_bytes = certificate_generator.generate(
        recipient_name="Alexander Hamilton",
        event_name="Constitutional Law & Governance",
        issuer_name="National Academy",
        certificate_title="Certificate of Excellence",
        issue_date=date(2026, 10, 10),
        certificate_id="CERT-2026-TEST01",
        output_path=pdf_path,
        verification_url="https://verify.cert/CERT-2026-TEST01",
    )

    # Assert standard PDF magic number header
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000
    assert pdf_path.is_file()
    assert pdf_path.stat().st_size == len(pdf_bytes)


def test_pdf_dynamic_scaling_long_name():
    """Test that generator gracefully handles exceptionally long recipient names without crashing."""
    long_name = (
        "Sir Bartholomew Montgomery Chichester-Smythe the Third, Grand Chancellor"
    )
    pdf_bytes = certificate_generator.generate(
        recipient_name=long_name,
        event_name="Advanced Astrophysics and Quantum Computing Seminar",
        issuer_name="International Science Foundation",
        certificate_title="Certificate of Achievement",
        issue_date=date.today(),
        certificate_id="CERT-LONG-NAME-01",
    )

    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000
