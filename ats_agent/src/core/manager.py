"""ATS Agent Manager for orchestrating agent operations and streaming.

This module provides the AgentManager class that handles streaming responses,
conversation management, and the coordination between the LangGraph agent
and the REST API endpoints.
"""

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from typing import Any, Dict, Optional
from uuid import uuid4

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langfuse.callback import CallbackHandler

from ats_agent.src.core.agent import get_global_ats_agent, ATSAgent
from ats_agent.src.schema import (
    ATSAnalysisResult,
    ATSRequest,
    ATSScores,
    KeywordAnalysis,
    MessageType,
    SkillsAnalysis,
    StreamMessage,
)
from ats_agent.src.settings import settings
from ats_agent.src.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize Langfuse callback handler if enabled
langfuse_handler = None
if settings.langfuse_enabled:
    langfuse_handler = CallbackHandler(
        trace_name="ats-agent",
        environment=settings.LANGFUSE_TRACING_ENVIRONMENT
    )


class ATSAgentManager:
    """Manager for ATS agent operations with streaming and enterprise features.
    
    This class provides a high-level interface for ATS agent operations,
    handling streaming responses, conversation persistence, and error management.
    """
    
    def __init__(self):
        self.agent: Optional[ATSAgent] = None
        self._request_counter = 0
    
    async def initialize(self):
        """Initialize the agent manager and underlying agent."""
        if self.agent is None:
            self.agent = await get_global_ats_agent()
            logger.info("ATS Agent Manager initialized")
    
    async def stream_analysis(self, request: ATSRequest) -> AsyncGenerator[str, None]:
        """Stream ATS analysis results in real-time using Server-Sent Events.
        
        Args:
            request: ATS analysis request
            
        Yields:
            Server-Sent Event formatted strings for streaming
        """
        await self.initialize()
        
        request_id = str(uuid4())
        self._request_counter += 1
        
        logger.info(f"Starting streaming analysis {request_id} for user {request.user_id}")
        
        try:
            # Send initial progress message
            yield self._format_sse_message({
                "type": MessageType.PROGRESS,
                "content": {"message": "Initializing ATS analysis...", "progress": 10}
            })
            
            # Prepare analysis prompt with request context
            analysis_prompt = self._build_analysis_prompt(request)
            
            # Configure LangGraph run
            config = RunnableConfig(
                configurable={
                    "thread_id": request.thread_id or f"thread_{request_id}",
                    "user_id": request.user_id or "anonymous"
                }
            )
            
            # Add Langfuse callback if enabled
            if langfuse_handler:
                config["callbacks"] = [langfuse_handler]
            
            yield self._format_sse_message({
                "type": MessageType.PROGRESS,
                "content": {"message": "Processing resume and job description...", "progress": 30}
            })
            
            # Stream the agent response
            token_buffer = ""
            message_content = ""
            
            async for chunk in self.agent.stream_analysis(
                resume_text=request.resume_text or "",
                job_description=request.job_description or "",
                thread_id=request.thread_id,
            ):
                try:
                    # Handle different chunk types from LangGraph
                    if "messages" in chunk:
                        messages = chunk["messages"]
                        if messages and isinstance(messages[-1], AIMessage):
                            ai_message = messages[-1]
                            
                            # Handle streaming tokens
                            if hasattr(ai_message, 'content') and ai_message.content:
                                content = ai_message.content
                                
                                if request.stream_tokens:
                                    # Stream individual tokens
                                    new_content = content[len(message_content):]
                                    if new_content:
                                        for char in new_content:
                                            token_buffer += char
                                            if len(token_buffer) >= 5 or char in ['.', '\n', '!', '?']:
                                                yield self._format_sse_message({
                                                    "type": MessageType.TOKEN,
                                                    "content": token_buffer
                                                })
                                                token_buffer = ""
                                        
                                        message_content = content
                                
                                # Send complete message periodically
                                yield self._format_sse_message({
                                    "type": MessageType.MESSAGE,
                                    "content": {
                                        "type": "ai",
                                        "content": content,
                                        "metadata": {
                                            "request_id": request_id,
                                            "thread_id": request.thread_id
                                        }
                                    }
                                })
                    
                    # Send progress updates
                    if self._request_counter % 10 == 0:
                        yield self._format_sse_message({
                            "type": MessageType.PROGRESS,
                            "content": {"message": "Analyzing...", "progress": 70}
                        })
                
                except Exception as e:
                    logger.error(f"Error processing chunk: {e}")
                    continue
            
            # Flush any remaining tokens
            if token_buffer:
                yield self._format_sse_message({
                    "type": MessageType.TOKEN,
                    "content": token_buffer
                })
            
            # Send completion message
            yield self._format_sse_message({
                "type": MessageType.PROGRESS,
                "content": {"message": "Analysis complete", "progress": 100}
            })
            
            # Final message
            yield self._format_sse_message({
                "type": MessageType.MESSAGE,
                "content": {
                    "type": "ai",
                    "content": message_content,
                    "metadata": {
                        "request_id": request_id,
                        "thread_id": request.thread_id,
                        "status": "completed"
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"Streaming analysis failed: {e}")
            yield self._format_sse_message({
                "type": MessageType.ERROR,
                "content": {
                    "error": "Analysis failed",
                    "message": str(e),
                    "request_id": request_id
                }
            })
        
        finally:
            # Send completion marker
            yield "data: [DONE]\n\n"
    
    async def analyze_resume_complete(self, request: ATSRequest) -> ATSAnalysisResult:
        """Perform complete ATS analysis and return structured results.
        
        Args:
            request: ATS analysis request
            
        Returns:
            Complete ATS analysis results
            
        Raises:
            Exception: If analysis fails
        """
        await self.initialize()
        
        request_id = str(uuid4())
        logger.info(f"Starting complete analysis {request_id}")
        
        try:
            t0 = time.perf_counter()
            result = await self.agent.analyze_resume(
                resume_text=request.resume_text or "",
                job_description=request.job_description or "",
                thread_id=request.thread_id,
                user_id=request.user_id,
            )
            elapsed = time.perf_counter() - t0
            analysis_text = result.get("analysis", "")

            analysis_result = ATSAnalysisResult(
                request_id=request_id,
                analysis_type=request.analysis_type,
                scores=ATSScores(
                    overall_score=0,
                    keyword_score=0,
                    skills_score=0,
                    format_score=0,
                    experience_score=0,
                    grade="—",
                    percentile=0,
                ),
                keyword_analysis=KeywordAnalysis(
                    matched_keywords=[],
                    missing_keywords=[],
                    match_score=0,
                    total_job_keywords=0,
                    keyword_density=0.0,
                ),
                skills_analysis=SkillsAnalysis(
                    present_skills=[],
                    missing_skills=[],
                ),
                recommendations=[],
                strengths=[],
                weaknesses=[],
                summary=analysis_text,
                processing_time=elapsed,
            )

            return analysis_result
            
        except Exception as e:
            logger.error(f"Complete analysis failed: {e}")
            raise
    
    async def get_conversation_history(self, thread_id: str) -> list:
        """Get conversation history for a thread.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            List of conversation messages
        """
        await self.initialize()
        
        try:
            return await self.agent.get_conversation_history(thread_id)
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    def _build_analysis_prompt(self, request: ATSRequest) -> str:
        """Build analysis prompt based on request parameters.
        
        Args:
            request: ATS analysis request
            
        Returns:
            Formatted analysis prompt
        """
        base_prompt = f"""
        User message: {request.message}
        
        Please analyze the following resume against the job description:

        **Resume:**
        {request.resume_text or '[Resume content to be uploaded]'}

        **Job Description:**
        {request.job_description}

        Analysis type: {request.analysis_type.value}
        
        Please provide comprehensive ATS feedback with specific scores and recommendations.
        """
        
        return base_prompt.strip()
    
    def _format_sse_message(self, message_data: Dict[str, Any]) -> str:
        """Format message for Server-Sent Events streaming.
        
        Args:
            message_data: Message data to format
            
        Returns:
            SSE-formatted string
        """
        json_data = json.dumps(message_data, ensure_ascii=False)
        return f"data: {json_data}\n\n"
    
    async def cleanup(self):
        """Clean up manager resources."""
        if self.agent:
            await self.agent.cleanup()
            logger.info("ATS Agent Manager cleaned up")


# Global manager instance
_global_manager: Optional[ATSAgentManager] = None


async def get_global_manager() -> ATSAgentManager:
    """Get or create global ATS agent manager.
    
    Returns:
        Global manager instance
    """
    global _global_manager
    
    if _global_manager is None:
        _global_manager = ATSAgentManager()
        await _global_manager.initialize()
    
    return _global_manager