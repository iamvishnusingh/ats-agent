# ATS Resume Reviewer Agent

FastAPI + LangGraph service that analyzes resumes against an optional job description. Supports **pasted text** or **HTTPS URLs** for resumes and job postings, optional **streaming** responses, and **OpenAI**, **Google (Gemini)**, or **local Ollama** as the LLM.

## Prerequisites

- **Python 3.10+**
- **No database required for local dev** if `USE_INMEMORY_SAVER=true` (default): LangGraph uses in-memory checkpoints only.
- **One LLM backend** (pick one):
  - **OpenAI:** `OPENAI_API_KEY`
  - **Gemini:** `GOOGLE_API_KEY` or `GEMINI_API_KEY` (same meaning in this project)
  - **Ollama (local):** `ollama serve` and a pulled model (e.g. `ollama pull llama3.2`)

## Install

### Option A — Make (same idea as [template-agent](https://github.com/redhat-data-and-ai/template-agent) `make install` / `make local`)

From the **repository root** (`ats-agent/`):

```bash
make install          # creates ./.venv and pip install -e ./ats_agent
# edit ats_agent/.env (API keys, LLM_PROVIDER, etc.)
make local            # copies .env.example → .env if missing, then runs the server
```

`make local` runs with `USE_INMEMORY_SAVER=true` and **working directory `ats_agent/`** so Pydantic loads `ats_agent/.env` correctly.

Other targets: `make clean`, `make test` (bytecode smoke compile).

### Option B — Manual venv

```bash
cd ats_agent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

## Configure

```bash
cp ats_agent/.env.example ats_agent/.env
# or, if you use make local without an existing .env, make will copy it for you
```

Edit `.env` at minimum:

| Variable | Purpose |
|----------|--------|
| `LLM_PROVIDER` | `auto` (default), `openai`, `google`, or `ollama`. `auto` picks OpenAI → Google → Ollama. |
| `OPENAI_API_KEY` | If using OpenAI. |
| `GOOGLE_API_KEY` or `GEMINI_API_KEY` | If using Gemini. |
| `DEFAULT_MODEL` | Model id for OpenAI/Gemini (e.g. `gpt-4o-mini`, `gemini-2.0-flash`). |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | When using Ollama (default base `http://localhost:11434`). |
| `USE_INMEMORY_SAVER` | Keep `true` for local use without PostgreSQL. |

## Run the API server

**If you used `make install`:** activate the **repo root** venv, then either:

```bash
source .venv/bin/activate
cd ats_agent && python -m ats_agent.src.main
```

**If you used manual install inside `ats_agent/.venv`:**

```bash
cd ats_agent && source .venv/bin/activate
ats-agent
# or: python -m ats_agent.src.main
```

Default URL: **http://localhost:8082** (see `AGENT_HOST` / `AGENT_PORT` in `.env`).

- Health: `GET http://localhost:8082/health`
- OpenAPI (development): `http://localhost:8082/docs`

## Call the API

### One-shot report (recommended)

`POST /v1/report` — returns JSON with a single `report` string (full model output).

**Resume:** provide `resume_text` and/or `resume_url` (public `https://` link to PDF/DOCX/TXT or HTML).

**Job (optional):** `job_description` and/or `job_description_url`. If both are omitted, a built-in general review prompt is used.

```bash
curl -s -X POST "http://localhost:8082/v1/report" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_url": "https://example.com/your-resume.pdf",
    "job_description_url": "https://example.com/job-posting"
  }'
```

With pasted text only:

```bash
curl -s -X POST "http://localhost:8082/v1/report" \
  -H "Content-Type: application/json" \
  -d '{
    "resume_text": "Your resume text here...",
    "job_description": "Paste job description here..."
  }'
```

### Streaming (SSE)

`POST /v1/stream` — same body shape as `/v1/report` (uses `ATSRequest`); response is Server-Sent Events.

### Synchronous structured payload

`POST /v1/analyze` — same resolution rules; returns the structured `ATSAnalysisResult` envelope (scores in the payload are placeholders unless you extend parsing).

## Legacy standalone script (optional)

The file **`ats_agent.py`** at the repo root is an older **NLTK/sklearn** scorer with an interactive CLI. It does not use the LangGraph/FastAPI stack. Prefer the **`ats_agent/`** package and the HTTP API above for the full agent.

## Project layout (high level)

```
ats-agent/
├── README.md                 # This file
├── ats_agent.py              # Legacy CLI scorer (optional)
├── ats_agent/                # Installable package (FastAPI + LangGraph)
│   ├── pyproject.toml
│   ├── .env.example
│   └── src/
│       ├── api.py
│       ├── main.py
│       ├── routes/           # /v1/report, /v1/stream, /v1/analyze, …
│       ├── core/             # agent, tools, prompts, resume_structure
│       └── utils/
└── test_data/
```

## Features (service)

- Resume: **text** or **URL** (PDF/DOCX/TXT or rough HTML text extraction).
- Job description: **text**, **URL**, or **omitted** (general ATS-style review).
- LangGraph agent with tools (documents, keywords, structured JSON helpers, etc.).
- Optional PostgreSQL only if you set `USE_INMEMORY_SAVER=false` and configure `POSTGRES_*`.

## License

See the license file in the repository you received (e.g. Apache 2.0 or as shipped by the project owner).
