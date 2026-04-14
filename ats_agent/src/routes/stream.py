"""Streaming endpoints for real-time ATS analysis.

This module provides Server-Sent Events (SSE) streaming endpoints
for real-time ATS resume analysis and feedback.
"""

import time
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ats_agent.src.core.manager import ATSAgentManager, get_global_manager
from ats_agent.src.schema import ATSRequest, ResumeReportResponse
from ats_agent.src.utils.logger import get_logger
from ats_agent.src.utils.source_resolver import normalize_ats_request_async

logger = get_logger(__name__)

router = APIRouter(tags=["Streaming"], prefix="/v1")


async def get_manager() -> ATSAgentManager:
    """Dependency to get ATS agent manager."""
    return await get_global_manager()


async def _resolved_request(request: ATSRequest) -> ATSRequest:
    try:
        normalized, _ = await normalize_ats_request_async(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "Validation Error", "message": str(exc)},
        ) from exc
    return normalized


@router.post("/report", response_model=ResumeReportResponse)
async def resume_report(
    request: ATSRequest,
    manager: ATSAgentManager = Depends(get_manager),
) -> ResumeReportResponse:
    """Return one consolidated resume report.

    Supply **resume_text** or **resume_url** (or both; text wins). Optionally
    supply **job_description** and/or **job_description_url** (text wins). If
    neither job field is set, a general-purpose review prompt is used.
    """
    request_id = str(uuid4())
    t0 = time.perf_counter()
    normalized, meta = await normalize_ats_request_async(request)
    result = await manager.agent.analyze_resume(
        resume_text=normalized.resume_text or "",
        job_description=normalized.job_description or "",
        thread_id=f"report-{request_id}",
        user_id=normalized.user_id,
    )
    elapsed = time.perf_counter() - t0
    return ResumeReportResponse(
        report=result.get("analysis", ""),
        request_id=request_id,
        resume_source=meta["resume_source"],
        job_description_source=meta["job_source"],
        processing_time_seconds=elapsed,
    )


@router.post("/stream")
async def stream_ats_analysis(
    request: ATSRequest,
    manager: ATSAgentManager = Depends(get_manager),
) -> StreamingResponse:
    """Stream ATS analysis results in real-time.

    Resume: **resume_text** and/or **resume_url**. Job: **job_description**
    and/or **job_description_url**; if omitted, a default general review prompt
    is used.
    """
    try:
        normalized = await _resolved_request(request)
        logger.info(
            "Starting streaming analysis for user %s, thread %s, analysis type %s",
            request.user_id,
            request.thread_id,
            request.analysis_type,
        )
        return StreamingResponse(
            content=manager.stream_analysis(normalized),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Streaming endpoint error: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal Server Error",
                "message": "Failed to start streaming analysis",
                "details": str(e),
            },
        ) from e


@router.post("/analyze")
async def analyze_resume_sync(
    request: ATSRequest,
    manager: ATSAgentManager = Depends(get_manager),
) -> dict:
    """Synchronous analysis; same inputs as ``/v1/stream`` and ``/v1/report``."""
    try:
        normalized = await _resolved_request(request)
        logger.info("Starting synchronous analysis for user %s", request.user_id)
        result = await manager.analyze_resume_complete(normalized)
        return result.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Synchronous analysis failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail={"error": "Analysis Failed", "message": str(e)},
        ) from e


@router.options("/stream")
async def stream_options():
    """Handle CORS preflight requests for streaming endpoint."""
    return {
        "message": "CORS preflight response",
        "methods": ["POST", "OPTIONS"],
        "headers": ["Content-Type"],
    }
