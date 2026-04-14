"""Load and render ATS-owned Jinja prompt templates (no third-party prompt text)."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_ENV: Environment | None = None


def _environment() -> Environment:
    global _ENV
    if _ENV is None:
        _ENV = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=False,
        )
    return _ENV


def render_resume_template(template_name: str, **variables: str) -> str:
    """Render a template under ``templates/`` (with or without ``.jinja``)."""
    name = template_name if template_name.endswith(".jinja") else f"{template_name}.jinja"
    return _environment().get_template(name).render(**variables)


def list_resume_template_names() -> list[str]:
    """Return sorted ``*.jinja`` basenames in ``templates/``."""
    return sorted(p.name for p in _TEMPLATES_DIR.glob("*.jinja") if p.is_file())
