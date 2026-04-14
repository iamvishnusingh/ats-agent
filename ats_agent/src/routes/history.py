"""Conversation history endpoints for the ATS Agent.

This module provides endpoints for retrieving and managing
conversation history and chat threads.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime

from ats_agent.src.core.manager import get_global_manager, ATSAgentManager
from ats_agent.src.schema import ThreadResponse
from ats_agent.src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["History"], prefix="/v1")


async def get_manager() -> ATSAgentManager:
    """Dependency to get ATS agent manager."""
    return await get_global_manager()


@router.get("/history/{thread_id}")
async def get_conversation_history(
    thread_id: str,
    limit: Optional[int] = Query(default=50, description="Maximum number of messages to return"),
    offset: Optional[int] = Query(default=0, description="Number of messages to skip"),
    manager: ATSAgentManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Get conversation history for a specific thread.
    
    Args:
        thread_id: Thread identifier
        limit: Maximum number of messages to return
        offset: Number of messages to skip for pagination
        manager: ATS agent manager dependency
        
    Returns:
        Conversation history with messages and metadata
        
    Raises:
        HTTPException: If thread not found or retrieval fails
    """
    try:
        if not thread_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Thread ID is required"
            )
        
        logger.info(f"Retrieving history for thread {thread_id}")
        
        # Get conversation history
        messages = await manager.get_conversation_history(thread_id)
        
        # Apply pagination
        total_messages = len(messages)
        paginated_messages = messages[offset:offset + limit]
        
        # Format response
        response = {
            "thread_id": thread_id,
            "total_messages": total_messages,
            "returned_messages": len(paginated_messages),
            "offset": offset,
            "limit": limit,
            "messages": paginated_messages,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Retrieved {len(paginated_messages)} messages for thread {thread_id}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation history for thread {thread_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "History Retrieval Failed",
                "message": str(e),
                "thread_id": thread_id
            }
        )


@router.get("/threads/{user_id}")
async def get_user_threads(
    user_id: str,
    limit: Optional[int] = Query(default=20, description="Maximum number of threads to return"),
    offset: Optional[int] = Query(default=0, description="Number of threads to skip"),
    manager: ATSAgentManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Get all conversation threads for a user.
    
    Args:
        user_id: User identifier
        limit: Maximum number of threads to return
        offset: Number of threads to skip for pagination
        manager: ATS agent manager dependency
        
    Returns:
        List of user's conversation threads
        
    Raises:
        HTTPException: If user not found or retrieval fails
    """
    try:
        if not user_id.strip():
            raise HTTPException(
                status_code=400,
                detail="User ID is required"
            )
        
        logger.info(f"Retrieving threads for user {user_id}")
        
        # In a real implementation, this would query the database
        # For now, return a mock response
        threads = [
            {
                "thread_id": f"thread_{user_id}_1",
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "message_count": 5,
                "title": "Resume Analysis - Software Engineer",
                "status": "active"
            }
        ]
        
        # Apply pagination
        total_threads = len(threads)
        paginated_threads = threads[offset:offset + limit]
        
        response = {
            "user_id": user_id,
            "total_threads": total_threads,
            "returned_threads": len(paginated_threads),
            "offset": offset,
            "limit": limit,
            "threads": paginated_threads,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Retrieved {len(paginated_threads)} threads for user {user_id}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get threads for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Thread Retrieval Failed",
                "message": str(e),
                "user_id": user_id
            }
        )


@router.delete("/history/{thread_id}")
async def delete_conversation_history(
    thread_id: str,
    manager: ATSAgentManager = Depends(get_manager)
) -> Dict[str, Any]:
    """Delete conversation history for a specific thread.
    
    Args:
        thread_id: Thread identifier
        manager: ATS agent manager dependency
        
    Returns:
        Deletion confirmation
        
    Raises:
        HTTPException: If deletion fails
    """
    try:
        if not thread_id.strip():
            raise HTTPException(
                status_code=400,
                detail="Thread ID is required"
            )
        
        logger.info(f"Deleting history for thread {thread_id}")
        
        # In a real implementation, this would delete from database
        # For now, return a mock response
        
        response = {
            "thread_id": thread_id,
            "deleted": True,
            "message": "Conversation history deleted successfully",
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Deleted history for thread {thread_id}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete history for thread {thread_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Deletion Failed",
                "message": str(e),
                "thread_id": thread_id
            }
        )


@router.post("/threads")
async def create_thread(
    user_id: Optional[str] = None,
    title: Optional[str] = None,
    manager: ATSAgentManager = Depends(get_manager)
) -> ThreadResponse:
    """Create a new conversation thread.
    
    Args:
        user_id: User identifier
        title: Optional thread title
        manager: ATS agent manager dependency
        
    Returns:
        Created thread information
        
    Raises:
        HTTPException: If thread creation fails
    """
    try:
        # Generate thread ID
        thread_id = f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id or 'anon'}"
        
        logger.info(f"Creating new thread {thread_id} for user {user_id}")
        
        # In a real implementation, this would create in database
        thread_response = ThreadResponse(
            thread_id=thread_id,
            user_id=user_id,
            created_at=datetime.now().isoformat(),
            message_count=0,
            last_activity=datetime.now().isoformat()
        )
        
        logger.info(f"Created thread {thread_id}")
        
        return thread_response
        
    except Exception as e:
        logger.error(f"Failed to create thread for user {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Thread Creation Failed",
                "message": str(e)
            }
        )