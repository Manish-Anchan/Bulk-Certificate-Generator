import io
from datetime import date
from pathlib import Path

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas


class CertificateGenerator:
    """High-performance vector PDF certificate renderer using ReportLab."""

    def __init__(self):
        # A4 Landscape: 841.89 x 595.28 points
        self.width, self.height = landscape(A4)

    def generate(
        self,
        recipient_name: str,
        event_name: str,
        issuer_name: str,
        certificate_title: str,
        issue_date: date,
        certificate_id: str,
        output_path: Path | str | None = None,
        verification_url: str | None = None,
    ) -> bytes:
        """Render a single vector PDF certificate and optionally save to disk.

        Args:
            recipient_name: Full name of the recipient.
            event_name: Event or course title.
            issuer_name: Issuing organization.
            certificate_title: Main certificate header (e.g. Certificate of Completion).
            issue_date: Date of issue.
            certificate_id: Unique certificate credential identifier.
            output_path: Optional file path to write the PDF to.
            verification_url: Optional URL to encode in the verification QR code.

        Returns:
            Raw bytes of the generated PDF.
        """
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=(self.width, self.height))

        # 1. Background fill
        c.setFillColor(colors.HexColor("#FCFDFD"))
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)

        # 2. Outer & Inner Borders
        self._draw_borders(c)

        # 3. Header & Issuer
        self._draw_header(c, issuer_name)

        # 4. Certificate Title
        self._draw_title(c, certificate_title)

        # 5. Presentation text & Recipient Name
        self._draw_recipient(c, recipient_name)

        # 6. Event description
        self._draw_event_details(c, event_name)

        # 7. Verification QR Code & Certificate Metadata
        self._draw_footer(c, issue_date, certificate_id, verification_url)

        c.showPage()
        c.save()

        pdf_bytes = buffer.getvalue()
        buffer.close()

        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(pdf_bytes)

        return pdf_bytes

    def _draw_borders(self, c: canvas.Canvas) -> None:
        """Draw professional double border with gold accents."""
        # Primary outer border (Deep Navy)
        c.setStrokeColor(colors.HexColor("#1A365D"))
        c.setLineWidth(3)
        c.rect(20, 20, self.width - 40, self.height - 40)

        # Secondary inner border (Refined Gold)
        c.setStrokeColor(colors.HexColor("#D4AF37"))
        c.setLineWidth(1)
        c.rect(26, 26, self.width - 52, self.height - 52)

        # Corner geometric accents
        accent_size = 14
        c.setFillColor(colors.HexColor("#1A365D"))
        for x, y in [
            (26, 26),
            (self.width - 26 - accent_size, 26),
            (26, self.height - 26 - accent_size),
            (self.width - 26 - accent_size, self.height - 26 - accent_size),
        ]:
            c.rect(x, y, accent_size, accent_size, fill=1, stroke=0)

    def _draw_header(self, c: canvas.Canvas, issuer_name: str) -> None:
        """Draw top issuing organization header."""
        c.setFillColor(colors.HexColor("#4A5568"))
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(self.width / 2, self.height - 75, issuer_name.upper())

        # Subtle gold divider
        c.setStrokeColor(colors.HexColor("#D4AF37"))
        c.setLineWidth(1)
        c.line(self.width / 2 - 80, self.height - 85, self.width / 2 + 80, self.height - 85)

    def _draw_title(self, c: canvas.Canvas, certificate_title: str) -> None:
        """Draw large certificate title."""
        c.setFillColor(colors.HexColor("#1A365D"))
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(self.width / 2, self.height - 135, certificate_title.upper())

        c.setFillColor(colors.HexColor("#718096"))
        c.setFont("Helvetica", 11)
        c.drawCentredString(self.width / 2, self.height - 165, "THIS IS PROUDLY PRESENTED TO")

    def _draw_recipient(self, c: canvas.Canvas, recipient_name: str) -> None:
        """Draw centered recipient name with dynamic font scaling to prevent overflow."""
        c.setFillColor(colors.HexColor("#0F172A"))

        # Dynamic font scaling if name is very long
        font_size = 32
        if len(recipient_name) > 30:
            font_size = 24
        elif len(recipient_name) > 20:
            font_size = 28

        c.setFont("Times-BoldItalic", font_size)
        y_pos = self.height - 220
        c.drawCentredString(self.width / 2, y_pos, recipient_name)

        # Decorative underline below name
        name_width = min(c.stringWidth(recipient_name, "Times-BoldItalic", font_size), 450)
        c.setStrokeColor(colors.HexColor("#D4AF37"))
        c.setLineWidth(1.5)
        c.line(
            self.width / 2 - (name_width / 2) - 20,
            y_pos - 10,
            self.width / 2 + (name_width / 2) + 20,
            y_pos - 10,
        )

    def _draw_event_details(self, c: canvas.Canvas, event_name: str) -> None:
        """Draw participation statement and event title."""
        c.setFillColor(colors.HexColor("#4A5568"))
        c.setFont("Helvetica", 12)
        c.drawCentredString(
            self.width / 2,
            self.height - 275,
            "for successfully participating in and completing",
        )

        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(self.width / 2, self.height - 310, event_name)

    def _draw_footer(
        self,
        c: canvas.Canvas,
        issue_date: date,
        certificate_id: str,
        verification_url: str | None,
    ) -> None:
        """Draw verification QR code, issue date, credential ID, and signature line."""
        # 1. Left side: Date & Certificate ID
        c.setFillColor(colors.HexColor("#64748B"))
        c.setFont("Helvetica", 9)
        c.drawString(60, 95, f"Date Issued: {issue_date.strftime('%B %d, %Y')}")
        c.drawString(60, 80, f"Certificate ID: {certificate_id}")

        # 2. Right side: Signature block
        sig_line_x = self.width - 240
        c.setStrokeColor(colors.HexColor("#94A3B8"))
        c.setLineWidth(1)
        c.line(sig_line_x, 100, sig_line_x + 180, 100)

        c.setFillColor(colors.HexColor("#1E293B"))
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(sig_line_x + 90, 85, "Authorized Signatory")
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawCentredString(sig_line_x + 90, 72, "Verification Authority")

        # 3. Center: Dynamic QR code for verification
        qr_url = verification_url or f"https://verify.cert/{certificate_id}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=3,
            border=1,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1A365D", back_color="white")

        qr_buffer = io.BytesIO()
        img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        # Draw QR code image onto canvas
        from reportlab.lib.utils import ImageReader
        qr_image = ImageReader(qr_buffer)
        qr_size = 55
        qr_x = self.width / 2 - (qr_size / 2)
        c.drawImage(qr_image, qr_x, 50, width=qr_size, height=qr_size)

        c.setFont("Helvetica", 7)
        c.setFillColor(colors.HexColor("#94A3B8"))
        c.drawCentredString(self.width / 2, 40, "Scan to Verify Credential")


# Singleton instance
certificate_generator = CertificateGenerator()
