"""ATS Agent implementation using LangChain and LangGraph.

This module provides the core ATS agent functionality with conversation
management, streaming capabilities, and enterprise features.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from ats_agent.src.core.exceptions import ATSAgentError, ATSAgentConfigError
from ats_agent.src.core.llm import get_llm
from ats_agent.src.core.prompt import get_ats_system_prompt
from ats_agent.src.core.prompt_templates import (
    build_resume_analysis_human_message,
    build_stream_resume_analysis_human_message,
)
from ats_agent.src.core.tools import get_ats_tools
from ats_agent.src.settings import settings
from ats_agent.src.utils.logger import get_logger

logger = get_logger(__name__)


async def initialize_database() -> None:
    """Initialize PostgreSQL database schema for checkpointing.
    
    This function creates the necessary tables and indexes for
    conversation persistence when using PostgreSQL storage.
    
    Raises:
        ATSAgentError: If database initialization fails.
    """
    if settings.USE_INMEMORY_SAVER:
        logger.info("Using in-memory storage - skipping database initialization")
        return

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    except ModuleNotFoundError as e:
        raise ATSAgentConfigError(
            "PostgreSQL checkpointing requires optional LangGraph postgres support. "
            "Install `langgraph-checkpoint-postgres` (see LangGraph docs), or set "
            "USE_INMEMORY_SAVER=true."
        ) from e

    try:
        logger.info("Initializing PostgreSQL database schema")
        async with AsyncPostgresSaver.from_conn_string(
            settings.database_uri
        ) as checkpoint:
            if hasattr(checkpoint, "setup"):
                await checkpoint.setup()
                logger.info("Database schema initialized successfully")
            else:
                logger.warning(
                    "AsyncPostgresSaver does not have setup method - "
                    "schema may need manual creation"
                )
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise ATSAgentError(f"Database initialization failed: {e}") from e


async def get_checkpointer():
    """Get configured checkpointer for conversation persistence.
    
    Returns:
        Checkpointer instance (MemorySaver or AsyncPostgresSaver).
    """
    if settings.USE_INMEMORY_SAVER:
        logger.info("Using in-memory checkpointer")
        return MemorySaver()

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    except ModuleNotFoundError as e:
        raise ATSAgentConfigError(
            "PostgreSQL checkpointing requires optional LangGraph postgres support. "
            "Install `langgraph-checkpoint-postgres`, or set USE_INMEMORY_SAVER=true."
        ) from e

    logger.info("Using PostgreSQL checkpointer")
    return AsyncPostgresSaver.from_conn_string(settings.database_uri)


async def create_ats_agent():
    """Create and configure the ATS agent with tools and checkpointing.
    
    Returns:
        Configured LangGraph agent ready for use.
        
    Raises:
        ATSAgentError: If agent creation fails.
    """
    try:
        # Get LLM instance
        llm = get_llm()
        
        # Get system prompt
        system_prompt = get_ats_system_prompt()
        
        # Get ATS-specific tools
        tools = get_ats_tools()
        
        # Get checkpointer
        checkpointer = await get_checkpointer()
        
        # Create agent
        agent = create_react_agent(
            model=llm,
            tools=tools,
            checkpointer=checkpointer,
            state_modifier=system_prompt,
        )
        
        logger.info("ATS agent created successfully")
        return agent
        
    except Exception as e:
        logger.error(f"Failed to create ATS agent: {e}")
        raise ATSAgentError(f"Agent creation failed: {e}") from e


@asynccontextmanager
async def get_ats_agent():
    """Context manager for ATS agent lifecycle.
    
    Yields:
        Configured ATS agent instance.
    """
    agent = None
    try:
        agent = await create_ats_agent()
        yield agent
    except Exception as e:
        logger.error(f"ATS agent error: {e}")
        raise
    finally:
        if agent and hasattr(agent, 'cleanup'):
            try:
                await agent.cleanup()
            except Exception as e:
                logger.error(f"Error during agent cleanup: {e}")


class ATSAgent:
    """High-level ATS Agent interface for business logic.
    
    This class provides a simplified interface for ATS operations
    while managing the underlying LangGraph agent complexity.
    """
    
    def __init__(self):
        self._agent = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the ATS agent."""
        if self._initialized:
            return
        
        try:
            self._agent = await create_ats_agent()
            self._initialized = True
            logger.info("ATS Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ATS Agent: {e}")
            raise ATSAgentError(f"Initialization failed: {e}") from e
    
    async def analyze_resume(
        self,
        resume_text: str,
        job_description: str,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze resume against job description.
        
        Args:
            resume_text: Text content of the resume
            job_description: Job description to match against
            thread_id: Optional thread ID for conversation
            user_id: Optional user identifier
            
        Returns:
            Dictionary containing analysis results
            
        Raises:
            ATSAgentError: If analysis fails
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            human_message = build_resume_analysis_human_message(
                resume_text=resume_text,
                job_description=job_description,
            )

            # Configure run
            config = {"configurable": {"thread_id": thread_id or "default"}}
            
            # Run analysis
            response = await self._agent.ainvoke(
                {"messages": [human_message]},
                config=config
            )
            
            # Extract and structure response
            ai_message = response["messages"][-1]
            
            result = {
                "analysis": ai_message.content,
                "thread_id": thread_id,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "status": "completed"
            }
            
            logger.info(f"Resume analysis completed for thread {thread_id}")
            return result
            
        except Exception as e:
            logger.error(f"Resume analysis failed: {e}")
            raise ATSAgentError(f"Analysis failed: {e}") from e
    
    async def stream_analysis(
        self,
        resume_text: str,
        job_description: str,
        thread_id: Optional[str] = None,
    ):
        """Stream resume analysis results in real-time.
        
        Args:
            resume_text: Text content of the resume
            job_description: Job description to match against
            thread_id: Optional thread ID for conversation
            
        Yields:
            Streaming analysis results
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            human_message = build_stream_resume_analysis_human_message(
                resume_text=resume_text,
                job_description=job_description,
            )

            config = {"configurable": {"thread_id": thread_id or "default"}}
            
            async for chunk in self._agent.astream(
                {"messages": [human_message]},
                config=config
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Streaming analysis failed: {e}")
            raise ATSAgentError(f"Streaming failed: {e}") from e
    
    async def get_conversation_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a thread.
        
        Args:
            thread_id: Thread identifier
            
        Returns:
            List of conversation messages
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = await self._agent.aget_state(config)
            
            messages = []
            for msg in state.values.get("messages", []):
                messages.append({
                    "type": msg.__class__.__name__,
                    "content": msg.content,
                    "timestamp": getattr(msg, "timestamp", None)
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            raise ATSAgentError(f"History retrieval failed: {e}") from e
    
    async def cleanup(self):
        """Clean up agent resources."""
        try:
            if self._agent and hasattr(self._agent, 'cleanup'):
                await self._agent.cleanup()
            self._initialized = False
            logger.info("ATS Agent cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Global agent instance
_global_agent: Optional[ATSAgent] = None


async def get_global_ats_agent() -> ATSAgent:
    """Get or create global ATS agent instance.
    
    Returns:
        Global ATS agent instance
    """
    global _global_agent
    
    if _global_agent is None:
        _global_agent = ATSAgent()
        await _global_agent.initialize()
    
    return _global_agent