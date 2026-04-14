"""Run structured-resume LLM prompts (original templates only)."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Final

from langchain_core.messages import HumanMessage, SystemMessage

from ats_agent.src.core.exceptions import ATSAgentConfigError
from ats_agent.src.core.llm import get_llm
from ats_agent.src.core.resume_structure.loader import render_resume_template
from ats_agent.src.utils.logger import get_logger

logger = get_logger(__name__)

RESUME_SECTIONS: Final[tuple[str, ...]] = (
    "basics",
    "work",
    "education",
    "skills",
    "projects",
    "awards",
)

_SECTION_USER_TEMPLATE: Final[dict[str, str]] = {
    "basics": "extract_basics.jinja",
    "work": "extract_work.jinja",
    "education": "extract_education.jinja",
    "skills": "extract_skills.jinja",
    "projects": "extract_projects.jinja",
    "awards": "extract_awards.jinja",
}


def _strip_json_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```\s*$", "", t)
    return t.strip()


def _invoke_json_pref(system: str, user: str) -> Dict[str, Any]:
    llm = get_llm()
    resp = llm.invoke(
        [SystemMessage(content=system), HumanMessage(content=user)],
    )
    raw = _strip_json_fence(
        resp.content if isinstance(resp.content, str) else str(resp.content)
    )
    try:
        return {"success": True, "raw": raw, "parsed": json.loads(raw)}
    except json.JSONDecodeError as e:
        logger.warning("Structured resume LLM output was not valid JSON: %s", e)
        return {"success": True, "raw": raw, "parsed": None, "json_error": str(e)}


def run_resume_section_parse(resume_markdown: str, section: str) -> Dict[str, Any]:
    """Extract one JSON Resume–style section using product-owned prompts."""
    section = section.strip().lower()
    if section not in RESUME_SECTIONS:
        return {
            "success": False,
            "error": f"section must be one of: {', '.join(RESUME_SECTIONS)}",
        }
    system = render_resume_template(
        "parser_section_system.jinja", section_key=section
    )
    user_tpl = _SECTION_USER_TEMPLATE[section]
    user = render_resume_template(user_tpl, text_content=resume_markdown)
    try:
        return _invoke_json_pref(system, user)
    except ATSAgentConfigError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception("run_resume_section_parse failed")
        return {"success": False, "error": str(e)}


def run_resume_evaluation(resume_markdown: str) -> Dict[str, Any]:
    """Fairness-aware technical scorecard as JSON (product-owned rubric)."""
    system = render_resume_template("scorecard_system.jinja")
    user = render_resume_template("scorecard_user.jinja", text_content=resume_markdown)
    try:
        return _invoke_json_pref(system, user)
    except ATSAgentConfigError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception("run_resume_evaluation failed")
        return {"success": False, "error": str(e)}


def run_github_project_selection(projects_data: str) -> Dict[str, Any]:
    """Shortlist repositories from structured JSON (product-owned criteria)."""
    user = render_resume_template(
        "github_repo_shortlist.jinja", projects_data=projects_data
    )
    system = (
        "Follow the user instructions exactly. Respond with valid JSON only—"
        "no markdown, no commentary."
    )
    try:
        return _invoke_json_pref(system, user)
    except ATSAgentConfigError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception("run_github_project_selection failed")
        return {"success": False, "error": str(e)}
