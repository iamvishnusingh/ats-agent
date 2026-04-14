"""Resolve resume and job description from text and/or HTTP(S) URLs."""

from __future__ import annotations

import asyncio
import re
import tempfile
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlparse

import httpx

from ats_agent.src.schema import ATSRequest
from ats_agent.src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_JOB_DESCRIPTION = """No job description was provided. Produce a concise resume report focused on:
- ATS-friendly structure and headings
- Clarity, measurable outcomes, and strong verbs
- Skills presentation and obvious gaps to fill (without a target role)
- Formatting and length
End with 5 prioritized action items."""

_HTML_TAG_RE = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
_STYLE_TAG_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
_BRACKET_TAG_RE = re.compile(r"<[^>]+>")


def _html_to_text(html: str) -> str:
    t = _HTML_TAG_RE.sub(" ", html)
    t = _STYLE_TAG_RE.sub(" ", t)
    t = _BRACKET_TAG_RE.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def _fetch_url(url: str, timeout: float = 45.0) -> tuple[bytes, Optional[str]]:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            ctype = response.headers.get("content-type")
            if ctype:
                ctype = ctype.split(";")[0].strip().lower()
            return response.content, ctype
    except httpx.HTTPError as exc:
        raise ValueError(f"Could not download URL: {exc}") from exc


def _guess_extension(url: str, content_type: Optional[str]) -> str:
    path = urlparse(url).path.lower()
    for ext in (".pdf", ".docx", ".doc", ".txt", ".md"):
        if path.endswith(ext):
            return ext
    if content_type == "application/pdf":
        return ".pdf"
    if content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        return ".docx"
    if content_type == "application/msword":
        return ".doc"
    if content_type and content_type.startswith("text/"):
        return ".txt"
    return ".bin"


def _resume_text_from_bytes(data: bytes, suffix: str) -> str:
    """Turn downloaded bytes into plain text via ``extract_plain_text`` on a temp file."""
    from ats_agent.src.utils.document_extract import extract_plain_text

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(data)
        tmp.flush()
        tmp.close()
        return extract_plain_text(tmp.name)
    finally:
        try:
            Path(tmp.name).unlink(missing_ok=True)
        except OSError:
            pass


def resolve_resume_text(
    resume_text: Optional[str],
    resume_url: Optional[str],
) -> tuple[str, Literal["text", "url"]]:
    """Return plain resume text from pasted body and/or URL."""
    text = (resume_text or "").strip()
    if text:
        return text, "text"
    url = (resume_url or "").strip()
    if not url:
        raise ValueError("Provide resume_text or resume_url")
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("resume_url must start with http:// or https://")

    data, ctype = _fetch_url(url)
    ext = _guess_extension(url, ctype)

    if ext in (".pdf", ".docx", ".doc"):
        body = _resume_text_from_bytes(data, ext)
        if not body.strip():
            raise ValueError("Could not extract text from resume file at URL")
        return body, "url"

    if ctype and "html" in ctype:
        body = _html_to_text(data.decode("utf-8", errors="replace"))
        if len(body) < 50:
            raise ValueError("Very little text extracted from resume URL (HTML)")
        return body, "url"

    decoded = data.decode("utf-8", errors="replace")
    if not decoded.strip():
        raise ValueError("Empty response when fetching resume_url")
    return decoded.strip(), "url"


def resolve_job_description(
    job_description: Optional[str],
    job_description_url: Optional[str],
) -> tuple[str, Literal["text", "url", "default"]]:
    """Return job description text; use a neutral default when nothing supplied."""
    text = (job_description or "").strip()
    if text:
        return text, "text"
    url = (job_description_url or "").strip()
    if not url:
        return DEFAULT_JOB_DESCRIPTION, "default"
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("job_description_url must start with http:// or https://")
    data, ctype = _fetch_url(url)
    if ctype and "html" in ctype:
        body = _html_to_text(data.decode("utf-8", errors="replace"))
    else:
        body = data.decode("utf-8", errors="replace").strip()
    if not body.strip():
        raise ValueError("Could not read job description from URL")
    return body.strip(), "url"


async def normalize_ats_request_async(request: ATSRequest) -> tuple[ATSRequest, dict[str, str]]:
    """Fetch URLs in a thread pool and return an updated request plus source metadata."""

    def _sync() -> tuple[str, str, str, str]:
        resume_body, rs = resolve_resume_text(request.resume_text, request.resume_url)
        jd_body, js = resolve_job_description(
            request.job_description, request.job_description_url
        )
        return resume_body, rs, jd_body, js

    r, rs, j, js = await asyncio.to_thread(_sync)
    updated = request.model_copy(update={"resume_text": r, "job_description": j})
    return updated, {"resume_source": rs, "job_source": js}
