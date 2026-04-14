"""Feedback endpoints for the ATS Agent.

This module provides endpoints for collecting user feedback
on analysis results and overall service quality.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends

from ats_agent.src.schema import FeedbackRequest
from ats_agent.src.core.manager import get_global_manager, ATSAgentManager
from ats_agent.src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Feedback"], prefix="/v1")


async def get_manager() -> ATSAgentManager:
    """Dependency to get ATS agent manager."""
    return await get_global_manager()


@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    manager: ATSAgentManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Submit feedback on analysis results or service quality.
    
    Args:
        feedback: Feedback submission with rating and comments
        manager: ATS agent manager dependency
        
    Returns:
        Feedback submission confirmation
        
    Raises:
        HTTPException: If feedback submission fails
    """
    try:
        # Validate feedback
        if feedback.rating < 1 or feedback.rating > 5:
            raise HTTPException(
                status_code=400,
                detail="Rating must be between 1 and 5"
            )
        
        if not feedback.request_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Request ID is required"
            )
        
        # Log feedback submission
        logger.info(
            f"Feedback submitted for request {feedback.request_id}: "
            f"rating={feedback.rating}, type={feedback.feedback_type}"
        )
        
        # In a production system, this would:
        # 1. Store feedback in database
        # 2. Send to analytics/monitoring system
        # 3. Trigger improvement workflows if rating is low
        # 4. Update model performance metrics
        
        # For now, create a mock feedback record
        feedback_record = {
            "feedback_id": f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "request_id": feedback.request_id,
            "user_id": feedback.user_id,
            "rating": feedback.rating,
            "feedback_type": feedback.feedback_type,
            "comments": feedback.comments,
            "timestamp": datetime.now().isoformat(),
            "status": "received"
        }
        
        # If Langfuse is enabled, could send feedback there
        # langfuse_handler.score(
        #     trace_id=feedback.request_id,
        #     name="user_rating", 
        #     value=feedback.rating
        # )
        
        logger.info(f"Feedback recorded: {feedback_record['feedback_id']}")
        
        response = {
            "success": True,
            "feedback_id": feedback_record["feedback_id"],
            "message": "Thank you for your feedback!",
            "timestamp": datetime.now().isoformat()
        }
        
        # Add follow-up actions based on rating
        if feedback.rating <= 2:
            response["follow_up"] = {
                "message": "We're sorry the analysis didn't meet your expectations. Our team will review your feedback.",
                "contact_support": True
            }
            logger.warning(f"Low rating feedback received: {feedback.rating}/5 for {feedback.request_id}")
            
        elif feedback.rating >= 4:
            response["follow_up"] = {
                "message": "Great to hear the analysis was helpful! Consider sharing with colleagues.",
                "share_prompt": True
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Feedback Submission Failed",
                "message": str(e)
            }
        )


@router.get("/feedback/{request_id}")
async def get_feedback(
    request_id: str,
    manager: ATSAgentManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Get feedback submitted for a specific analysis request.
    
    Args:
        request_id: Analysis request identifier
        manager: ATS agent manager dependency
        
    Returns:
        Feedback information for the request
        
    Raises:
        HTTPException: If feedback retrieval fails
    """
    try:
        if not request_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Request ID is required"
            )
        
        logger.info(f"Retrieving feedback for request {request_id}")
        
        # In a real implementation, this would query the database
        # For now, return a mock response
        feedback_data = {
            "request_id": request_id,
            "feedback_count": 1,
            "average_rating": 4.5,
            "feedback_summary": {
                "excellent": 1,
                "good": 0, 
                "average": 0,
                "poor": 0,
                "terrible": 0
            },
            "latest_feedback": {
                "rating": 5,
                "feedback_type": "accuracy",
                "comments": "Very helpful analysis with actionable recommendations",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        logger.info(f"Retrieved feedback for request {request_id}")
        
        return feedback_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feedback retrieval failed for request {request_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Feedback Retrieval Failed",
                "message": str(e),
                "request_id": request_id
            }
        )


@router.get("/feedback/stats/summary")
async def get_feedback_statistics(
    days: Optional[int] = 30,
    manager: ATSAgentManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Get overall feedback statistics and trends.
    
    Args:
        days: Number of days to include in statistics (default 30)
        manager: ATS agent manager dependency
        
    Returns:
        Feedback statistics and trends
        
    Raises:
        HTTPException: If statistics retrieval fails
    """
    try:
        logger.info(f"Retrieving feedback statistics for last {days} days")
        
        # In a real implementation, this would aggregate from database
        # For now, return mock statistics
        stats = {
            "period": f"Last {days} days",
            "total_feedback": 156,
            "average_rating": 4.2,
            "response_rate": "23%",  # feedback / total requests
            "ratings_distribution": {
                "5_stars": 68,
                "4_stars": 52,
                "3_stars": 24,
                "2_stars": 8,
                "1_star": 4
            },
            "feedback_types": {
                "accuracy": 89,
                "usefulness": 45,
                "speed": 22
            },
            "trends": {
                "rating_trend": "+0.3",  # Change from previous period
                "volume_trend": "+15%"
            },
            "top_positive_keywords": [
                "helpful", "accurate", "actionable", "detailed", "professional"
            ],
            "top_improvement_areas": [
                "formatting suggestions", "industry-specific advice", "faster processing"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("Retrieved feedback statistics")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Feedback statistics retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Statistics Retrieval Failed",
                "message": str(e)
            }
        )