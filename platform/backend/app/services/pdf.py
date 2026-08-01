"""보고서 PDF 생성 (reportlab). 한글 폰트 있으면 사용."""
from __future__ import annotations

import io
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

_FONT = "Helvetica"
for _p in ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
           "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"):
    if os.path.exists(_p):
        try:
            pdfmetrics.registerFont(TTFont("Nanum", _p))
            _FONT = "Nanum"
            break
        except Exception:
            pass


def report_pdf(title: str, sections: list[tuple[str, list[str]]]) -> bytes:
    """title + (섹션명, 줄들) 목록 → PDF bytes."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    y = h - 25 * mm

    c.setFont(_FONT, 18)
    c.drawString(20 * mm, y, title)
    y -= 12 * mm

    for name, lines in sections:
        if y < 30 * mm:
            c.showPage(); y = h - 25 * mm
        c.setFont(_FONT, 13)
        c.setFillColorRGB(0.06, 0.43, 0.47)
        c.drawString(20 * mm, y, name)
        c.setFillColorRGB(0, 0, 0)
        y -= 8 * mm
        c.setFont(_FONT, 10.5)
        for ln in lines:
            if y < 20 * mm:
                c.showPage(); y = h - 25 * mm
                c.setFont(_FONT, 10.5)
            c.drawString(24 * mm, y, ln[:95])
            y -= 6 * mm
        y -= 4 * mm

    c.showPage()
    c.save()
    return buf.getvalue()
