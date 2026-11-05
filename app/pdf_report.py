"""Minimal stdlib PDF report generator (no external dependencies).

Renders a single A4 page of text lines using the built-in Helvetica fonts.
Text is encoded as Latin-1; characters outside Latin-1 are replaced with
question marks so habit names with emoji never break the file.
"""
from __future__ import annotations

PDF_VERSION = b"%PDF-1.4"
PAGE_WIDTH = 595   # A4 in points
PAGE_HEIGHT = 842
TOP_MARGIN = 800
LINE_HEIGHT = 18


def _escape(text: str) -> str:
    """Escape PDF string specials and fold the text down to Latin-1."""
    cleaned = (
        text.replace("\\", r"\\")
        .replace("(", r"\(")
        .replace(")", r"\)")
    )
    return cleaned.encode("latin-1", errors="replace").decode("latin-1")


def _content_stream(lines: list[tuple[str, int, int]]) -> bytes:
    """lines: (text, font_size, y) tuples -> one Tj command per line."""
    parts = []
    for text, size, y in lines:
        font = "F1" if size >= 14 else "F2"
        parts.append(
            f"BT /{font} {size} Tf 50 {y} Td ({_escape(text)}) Tj ET".encode("latin-1")
        )
    return b"\n".join(parts) + b"\n"


def build_report_pdf(lines: list[str], title: str = "HabitQuest Report") -> bytes:
    """Render `lines` of plain text as a one-page PDF with a bold title."""
    layout: list[tuple[str, int, int]] = [(title, 16, TOP_MARGIN)]
    y = TOP_MARGIN - LINE_HEIGHT * 2
    for line in lines:
        layout.append((line, 11, y))
        y -= LINE_HEIGHT
    stream = _content_stream(layout)

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 "
         + str(PAGE_WIDTH).encode() + b" " + str(PAGE_HEIGHT).encode()
         + b"] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream",
    ]

    out = bytearray(PDF_VERSION + b"\n")
    offsets = [0]
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)
