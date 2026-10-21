from __future__ import annotations

from io import BytesIO

import qrcode
from fastapi import Request
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

from app.models import Certificate, Training, User
from app.services.email import site_url

PAGE_SIZE = landscape(A4)
PRIMARY = HexColor("#00339F")
ACCENT = HexColor("#00B5AC")
INK = HexColor("#102A43")
MUTED = HexColor("#5B6B7C")
PAPER = HexColor("#F7FAFC")
WHITE = HexColor("#FFFFFF")
LINE = HexColor("#D9E2EC")


def verification_url(request: Request, code: str) -> str:
    return f"{site_url(request)}/verificar/{code.strip().upper()}"


def build_qr_png(url: str, *, box_size: int = 8) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#00339F", back_color="white")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _fit_font(
    pdf: canvas.Canvas,
    text: str,
    font: str,
    preferred: float,
    minimum: float,
    max_width: float,
) -> float:
    size = preferred
    while size > minimum and pdf.stringWidth(text, font, size) > max_width:
        size -= 0.5
    return size


def _draw_centered(
    pdf: canvas.Canvas,
    text: str,
    *,
    font: str,
    size: float,
    y: float,
    color: HexColor,
    max_width: float | None = None,
) -> None:
    pdf.setFillColor(color)
    if max_width is None:
        pdf.setFont(font, size)
        pdf.drawCentredString(PAGE_SIZE[0] / 2, y, text)
        return
    lines = simpleSplit(text, font, size, max_width)
    pdf.setFont(font, size)
    for line in lines:
        pdf.drawCentredString(PAGE_SIZE[0] / 2, y, line)
        y -= size * 1.2


def _draw_wrapped_left(
    pdf: canvas.Canvas,
    text: str,
    *,
    font: str,
    size: float,
    x: float,
    y: float,
    color: HexColor,
    max_width: float,
    max_lines: int = 2,
) -> None:
    lines = simpleSplit(text, font, size, max_width)[:max_lines]
    pdf.setFillColor(color)
    pdf.setFont(font, size)
    for line in lines:
        pdf.drawString(x, y, line)
        y -= size * 1.2


def build_certificate_pdf(
    certificate: Certificate,
    training: Training,
    employee: User,
    *,
    verify_url: str,
) -> bytes:
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=PAGE_SIZE)
    width, height = PAGE_SIZE
    margin = 22 * mm
    content_width = width - margin * 2
    code = certificate.verification_code

    pdf.setTitle(f"Certificado - {employee.name}")
    pdf.setAuthor("Universidade Lins")
    pdf.setSubject(f"Certificado de conclusão - {training.title}")
    pdf.setKeywords(f"{code}, certificado, {training.title}")

    pdf.setFillColor(PAPER)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    pdf.setFillColor(PRIMARY)
    pdf.rect(0, height - 34 * mm, width, 34 * mm, fill=1, stroke=0)
    pdf.setFillColor(ACCENT)
    pdf.rect(0, height - 37 * mm, width, 3 * mm, fill=1, stroke=0)

    pdf.setFillColor(WHITE)
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(margin, height - 19 * mm, "LINS")
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(margin, height - 25 * mm, "AGROINDUSTRIAL  |  UNIVERSIDADE LINS")
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawRightString(width - margin, height - 19 * mm, "CERTIFICADO DIGITAL")
    pdf.setFont("Helvetica", 7)
    pdf.drawRightString(
        width - margin,
        height - 25 * mm,
        "Documento emitido eletronicamente",
    )

    _draw_centered(
        pdf,
        "CERTIFICADO",
        font="Helvetica-Bold",
        size=27,
        y=height - 57 * mm,
        color=PRIMARY,
    )
    _draw_centered(
        pdf,
        "DE CONCLUSÃO",
        font="Helvetica-Bold",
        size=14,
        y=height - 65 * mm,
        color=ACCENT,
    )

    _draw_centered(
        pdf,
        "Certificamos que",
        font="Helvetica",
        size=10.5,
        y=height - 82 * mm,
        color=MUTED,
    )
    name_size = _fit_font(
        pdf,
        employee.name,
        "Helvetica-Bold",
        21,
        13,
        content_width - 20 * mm,
    )
    _draw_centered(
        pdf,
        employee.name,
        font="Helvetica-Bold",
        size=name_size,
        y=height - 94 * mm,
        color=PRIMARY,
    )
    _draw_centered(
        pdf,
        "concluiu com aproveitamento o treinamento",
        font="Helvetica",
        size=10.5,
        y=height - 106 * mm,
        color=MUTED,
    )

    title_size = 16
    title_lines = simpleSplit(training.title, "Helvetica-Bold", title_size, content_width)
    while title_size > 10 and len(title_lines) > 2:
        title_size -= 0.5
        title_lines = simpleSplit(training.title, "Helvetica-Bold", title_size, content_width)
    title_y = height - 116 * mm
    pdf.setFillColor(PRIMARY)
    pdf.setFont("Helvetica-Bold", title_size)
    for line in title_lines:
        pdf.drawCentredString(width / 2, title_y, line)
        title_y -= title_size * 1.25

    hours = f"{training.workload_hours:g}h"
    details = (
        f"Carga horária: {hours}   |   Data: {training.date.strftime('%d/%m/%Y')}"
        f"   |   Local: {training.location}"
    )
    details_size = _fit_font(pdf, details, "Helvetica", 9.5, 7.5, content_width)
    _draw_centered(
        pdf,
        details,
        font="Helvetica",
        size=details_size,
        y=height - 132 * mm,
        color=INK,
    )

    pdf.setStrokeColor(LINE)
    pdf.setLineWidth(0.7)
    pdf.line(margin, height - 140 * mm, width - margin, height - 140 * mm)

    pdf.setStrokeColor(PRIMARY)
    pdf.setLineWidth(0.8)
    pdf.line(margin, 56 * mm, margin + 72 * mm, 56 * mm)
    pdf.setFillColor(PRIMARY)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(margin, 50 * mm, "Universidade Lins")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(margin, 45 * mm, "Trilha de Talentos - Certificação")

    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica-Bold", 7.5)
    pdf.drawString(margin, 38 * mm, "CÓDIGO DE VERIFICAÇÃO")
    pdf.setFillColor(PRIMARY)
    pdf.setFont("Courier-Bold", 11)
    pdf.drawString(margin, 31 * mm, code)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(
        margin,
        24 * mm,
        f"Emitido em {certificate.issued_at.strftime('%d/%m/%Y')}",
    )
    _draw_wrapped_left(
        pdf,
        verify_url,
        font="Helvetica",
        size=6.5,
        x=margin,
        y=17 * mm,
        color=MUTED,
        max_width=content_width - 55 * mm,
        max_lines=1,
    )

    qr_size = 34 * mm
    qr_x = width - margin - qr_size
    qr_y = 30 * mm
    pdf.drawImage(
        ImageReader(BytesIO(build_qr_png(verify_url))),
        qr_x,
        qr_y,
        width=qr_size,
        height=qr_size,
        mask="auto",
    )
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 6.5)
    pdf.drawCentredString(qr_x + qr_size / 2, 24 * mm, "Aponte a câmera para validar")

    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 6.5)
    pdf.drawString(
        margin,
        11 * mm,
        "A autenticidade pode ser conferida pelo código ou pelo QR Code acima.",
    )
    pdf.drawRightString(width - margin, 11 * mm, "Página 1 de 1")

    pdf.showPage()
    pdf.save()
    return output.getvalue()
