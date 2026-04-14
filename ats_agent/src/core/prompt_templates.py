"""User-message prompts built with LangChain ChatPromptTemplate.

Use these instead of ad hoc f-strings so inputs are named, partial prompts can
be chained later (e.g. with Runnable), and escaping follows LangChain rules
(literal braces in the template must be doubled: {{ }}).
"""

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

RESUME_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "human",
            """Please analyze the following resume against the job description and provide comprehensive ATS feedback:

**Resume:**
{resume_text}

**Job Description:**
{job_description}

Please provide:
1. Overall ATS match score (0-100)
2. Keyword analysis (matched and missing)
3. Skills gap analysis
4. Specific recommendations for improvement
5. Strengths and weaknesses
6. Optimized professional summary""",
        )
    ]
)

STREAM_RESUME_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "human",
            """Analyze this resume against the job description with streaming output:

**Resume:** {resume_text}
**Job Description:** {job_description}

Provide comprehensive ATS analysis with real-time feedback.""",
        )
    ]
)


def build_resume_analysis_human_message(
    resume_text: str, job_description: str
) -> HumanMessage:
    """Format the main resume-vs-JD analysis as a HumanMessage."""
    messages = RESUME_ANALYSIS_PROMPT.format_messages(
        resume_text=resume_text,
        job_description=job_description,
    )
    return messages[0]


def build_stream_resume_analysis_human_message(
    resume_text: str, job_description: str
) -> HumanMessage:
    """Format the streaming analysis request as a HumanMessage."""
    messages = STREAM_RESUME_ANALYSIS_PROMPT.format_messages(
        resume_text=resume_text,
        job_description=job_description,
    )
    return messages[0]
