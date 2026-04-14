"""Schema definitions for the ATS Agent.

This module contains Pydantic models for request/response validation,
data serialization, and API documentation for the ATS agent service.
"""

from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from enum import Enum


class ATSAnalysisType(str, Enum):
    """Types of ATS analysis available."""
    FULL_ANALYSIS = "full_analysis"
    KEYWORD_MATCH = "keyword_match"
    SKILLS_ANALYSIS = "skills_analysis"
    QUICK_SCORE = "quick_score"


class FileFormat(str, Enum):
    """Supported file formats for resume upload."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class PriorityLevel(str, Enum):
    """Priority levels for recommendations."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MessageType(str, Enum):
    """Types of streaming messages."""
    TOKEN = "token"
    MESSAGE = "message"
    PROGRESS = "progress"
    ERROR = "error"
    DONE = "done"


class ATSRequest(BaseModel):
    """Request model for ATS analysis."""
    
    message: str = Field(
        default="Analyze my resume and produce a clear report.",
        description="User message or question about ATS analysis",
        examples=["Analyze my resume for this job"],
    )
    resume_text: Optional[str] = Field(
        default=None,
        description="Resume as plain text or markdown (optional if resume_url is set)",
    )
    resume_url: Optional[str] = Field(
        default=None,
        description="HTTP(S) URL to a resume (.pdf, .docx, .txt) or HTML/text page",
    )
    job_description: Optional[str] = Field(
        default=None,
        description="Job description text (optional if job_description_url is set)",
        examples=["Software Engineer position requiring Python, React..."],
    )
    job_description_url: Optional[str] = Field(
        default=None,
        description="HTTP(S) URL to a posting or job description page",
    )
    analysis_type: ATSAnalysisType = Field(
        default=ATSAnalysisType.FULL_ANALYSIS,
        description="Type of analysis to perform"
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Thread ID to continue conversation"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for tracking"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier"
    )
    stream_tokens: bool = Field(
        default=True,
        description="Enable token-by-token streaming"
    )

    @model_validator(mode="after")
    def _resume_source_present(self) -> "ATSRequest":
        has_text = bool((self.resume_text or "").strip())
        has_url = bool((self.resume_url or "").strip())
        if not has_text and not has_url:
            raise ValueError("Provide resume_text and/or resume_url")
        return self


class KeywordAnalysis(BaseModel):
    """Keyword analysis results."""
    
    matched_keywords: List[str] = Field(
        description="Keywords found in both resume and job description"
    )
    missing_keywords: List[str] = Field(
        description="Important keywords missing from resume"
    )
    match_score: int = Field(
        ge=0, le=100,
        description="Keyword match percentage (0-100)"
    )
    total_job_keywords: int = Field(
        description="Total keywords extracted from job description"
    )
    keyword_density: float = Field(
        description="Keyword density ratio"
    )


class SkillsAnalysis(BaseModel):
    """Skills gap analysis results."""
    
    present_skills: List[str] = Field(
        description="Technical skills found in resume"
    )
    missing_skills: List[str] = Field(
        description="Skills required by job but missing from resume"
    )
    skill_categories: dict = Field(
        default_factory=dict,
        description="Skills organized by category (technical, soft, etc.)"
    )
    proficiency_levels: dict = Field(
        default_factory=dict,
        description="Estimated proficiency levels for skills"
    )


class ATSScores(BaseModel):
    """Comprehensive ATS scoring results."""
    
    overall_score: int = Field(
        ge=0, le=100,
        description="Overall ATS compatibility score (0-100)"
    )
    keyword_score: int = Field(
        ge=0, le=100,
        description="Keyword matching score"
    )
    skills_score: int = Field(
        ge=0, le=100,
        description="Skills alignment score"
    )
    format_score: int = Field(
        ge=0, le=100,
        description="Format and structure score"
    )
    experience_score: int = Field(
        ge=0, le=100,
        description="Experience relevance score"
    )
    grade: str = Field(
        description="Letter grade (A+ to F)"
    )
    percentile: int = Field(
        ge=0, le=100,
        description="Percentile ranking"
    )


class Recommendation(BaseModel):
    """Individual recommendation item."""
    
    priority: PriorityLevel = Field(
        description="Priority level of this recommendation"
    )
    category: str = Field(
        description="Category (keywords, experience, format, etc.)"
    )
    title: str = Field(
        description="Brief title of the recommendation"
    )
    description: str = Field(
        description="Detailed description of what to improve"
    )
    impact: str = Field(
        description="Expected impact of implementing this change"
    )
    examples: List[str] = Field(
        default_factory=list,
        description="Specific examples or suggestions"
    )


class ATSAnalysisResult(BaseModel):
    """Complete ATS analysis results."""
    
    request_id: str = Field(
        description="Unique identifier for this analysis request"
    )
    analysis_type: ATSAnalysisType = Field(
        description="Type of analysis performed"
    )
    scores: ATSScores = Field(
        description="ATS compatibility scores"
    )
    keyword_analysis: KeywordAnalysis = Field(
        description="Keyword matching analysis"
    )
    skills_analysis: SkillsAnalysis = Field(
        description="Skills gap analysis"
    )
    recommendations: List[Recommendation] = Field(
        description="Prioritized improvement recommendations"
    )
    strengths: List[str] = Field(
        description="Resume strengths identified"
    )
    weaknesses: List[str] = Field(
        description="Areas for improvement"
    )
    summary: str = Field(
        description="Executive summary of the analysis"
    )
    processing_time: float = Field(
        description="Time taken to complete analysis (seconds)"
    )


class StreamMessage(BaseModel):
    """Streaming message format."""
    
    type: MessageType = Field(
        description="Type of streaming message"
    )
    content: Any = Field(
        description="Message content"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata"
    )


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(
        description="Health status",
        examples=["healthy"]
    )
    service: str = Field(
        description="Service name",
        examples=["ATS Resume Reviewer Agent"]
    )
    version: str = Field(
        description="Service version",
        examples=["1.0.0"]
    )
    timestamp: str = Field(
        description="Current timestamp"
    )


class ThreadResponse(BaseModel):
    """Thread management response."""
    
    thread_id: str = Field(
        description="Thread identifier"
    )
    user_id: Optional[str] = Field(
        description="User identifier"
    )
    created_at: str = Field(
        description="Thread creation timestamp"
    )
    message_count: int = Field(
        description="Number of messages in thread"
    )
    last_activity: str = Field(
        description="Last activity timestamp"
    )


class FeedbackRequest(BaseModel):
    """Feedback submission model."""
    
    request_id: str = Field(
        description="Analysis request ID"
    )
    rating: int = Field(
        ge=1, le=5,
        description="Rating from 1-5 stars"
    )
    feedback_type: str = Field(
        description="Type of feedback (accuracy, usefulness, etc.)"
    )
    comments: Optional[str] = Field(
        default=None,
        description="Additional comments"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier"
    )


class ResumeReportResponse(BaseModel):
    """Single-call resume report (markdown or plain text from the model)."""

    report: str = Field(description="Full resume report from the agent")
    request_id: str = Field(description="Unique id for this report run")
    resume_source: Literal["text", "url"] = Field(
        description="Whether resume body came from pasted text or from resume_url",
    )
    job_description_source: Literal["text", "url", "default"] = Field(
        description="Whether the job description came from text, a URL, or built-in default",
    )
    processing_time_seconds: float = Field(
        default=0.0,
        description="Wall time spent on resolution + model run",
    )


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(
        description="Error type"
    )
    message: str = Field(
        description="Error message"
    )
    details: Optional[dict] = Field(
        default=None,
        description="Additional error details"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Request ID for tracking"
    )