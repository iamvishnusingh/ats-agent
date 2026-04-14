#!/usr/bin/env python3
"""One-shot resume report: PDF/DOCX/TXT path or URL + optional job text (no LangGraph, no DB).

Load ``.env`` first, then set ``LLM_PROVIDER`` to ``openai``, ``google``, or ``ollama``.
``auto`` picks OpenAI if ``OPENAI_API_KEY`` is set, else Gemini if ``GOOGLE_API_KEY``
or ``GEMINI_API_KEY`` is set, else local Ollama. The LangGraph API uses the same
``get_llm()`` rules as this CLI. For local-only runs::

    ollama serve
    export LLM_PROVIDER=ollama
    export OLLAMA_MODEL=llama3.2
    python -m ats_agent.src.cli.report ./resume.pdf

Or with an API key only::

    export LLM_PROVIDER=auto
    export OPENAI_API_KEY=sk-...
    python -m ats_agent.src.cli.report ./resume.pdf --job-file posting.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _bootstrap_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    rs = str(repo_root)
    if rs not in sys.path:
        sys.path.insert(0, rs)


def main() -> None:
    _bootstrap_path()

    from dotenv import load_dotenv

    for env_dir in (Path.cwd(), Path(__file__).resolve().parents[3]):
        candidate = env_dir / ".env"
        if candidate.is_file():
            load_dotenv(candidate)
            break
    else:
        load_dotenv()

    from langchain_core.messages import HumanMessage, SystemMessage

    from ats_agent.src.utils.document_extract import extract_plain_text
    from ats_agent.src.core.prompt import get_ats_system_prompt
    from ats_agent.src.core.prompt_templates import build_resume_analysis_human_message
    from ats_agent.src.core.llm import get_llm
    from ats_agent.src.utils.source_resolver import (
        DEFAULT_JOB_DESCRIPTION,
        resolve_resume_text,
    )

    parser = argparse.ArgumentParser(
        description="Print a single ATS-style resume report (local LLM or cloud API)."
    )
    parser.add_argument(
        "resume",
        help="Path to .pdf / .docx / .txt or https URL to resume",
    )
    parser.add_argument(
        "-j",
        "--job",
        default=None,
        help="Job description text (optional)",
    )
    parser.add_argument(
        "-f",
        "--job-file",
        default=None,
        help="Path to a file containing job description (optional)",
    )
    args = parser.parse_args()

    resume_arg = args.resume.strip()
    if resume_arg.startswith(("http://", "https://")):
        resume_body, _src = resolve_resume_text(None, resume_arg)
    else:
        resume_body = extract_plain_text(resume_arg)

    if args.job_file:
        jd = Path(args.job_file).read_text(encoding="utf-8", errors="replace").strip()
    elif args.job:
        jd = args.job.strip()
    else:
        jd = DEFAULT_JOB_DESCRIPTION

    llm = get_llm()
    messages = [
        SystemMessage(content=get_ats_system_prompt()),
        build_resume_analysis_human_message(
            resume_text=resume_body,
            job_description=jd,
        ),
    ]
    result = llm.invoke(messages)
    text = result.content if isinstance(result.content, str) else str(result.content)
    print(text)


if __name__ == "__main__":
    main()
