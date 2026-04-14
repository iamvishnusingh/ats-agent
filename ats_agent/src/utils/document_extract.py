"""Extract plain text from resume files (PDF, DOCX, plain text)."""

from __future__ import annotations

from pathlib import Path
from typing import List


def extract_plain_text(file_path: str) -> str:
    """Read a local file and return UTF-8 text (PDF/DOCX via pdfplumber / python-docx)."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import pdfplumber

        parts: List[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t.strip():
                    parts.append(t)
        return "\n\n".join(parts).strip()
    if suffix in (".docx", ".doc"):
        import docx

        document = docx.Document(str(path))
        return "\n".join(p.text for p in document.paragraphs if p.text.strip())
    return path.read_text(encoding="utf-8", errors="replace").strip()
