"""Main entry point for the ATS Agent service.

This module provides the main entry point for running the ATS agent
as a production service with proper configuration and monitoring.
"""

import asyncio
import signal
import sys
from typing import Optional
import uvicorn
from pathlib import Path

from ats_agent.src.api import app
from ats_agent.src.settings import settings
from ats_agent.src.utils.logger import get_logger

logger = get_logger(__name__)


class ATSAgentService:
    """Main service class for the ATS Agent."""
    
    def __init__(self):
        self.server: Optional[uvicorn.Server] = None
        self.should_shutdown = False
    
    async def start(self):
        """Start the ATS Agent service."""
        logger.info("Starting ATS Resume Reviewer Agent Service")
        
        try:
            # Configure uvicorn server
            config = uvicorn.Config(
                app=app,
                host=settings.AGENT_HOST,
                port=settings.AGENT_PORT,
                log_level=settings.PYTHON_LOG_LEVEL.lower(),
                reload=settings.is_development,
                ssl_keyfile=settings.AGENT_SSL_KEYFILE,
                ssl_certfile=settings.AGENT_SSL_CERTFILE,
                access_log=True,
                use_colors=True,
                loop="asyncio"
            )
            
            # Create server
            self.server = uvicorn.Server(config)
            
            # Setup signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Log startup information
            self._log_startup_info()
            
            # Start server
            logger.info(f"Server starting on {settings.AGENT_HOST}:{settings.AGENT_PORT}")
            await self.server.serve()
            
        except Exception as e:
            logger.error(f"Failed to start service: {e}")
            raise
    
    async def shutdown(self):
        """Gracefully shutdown the service."""
        logger.info("Shutting down ATS Agent Service")
        
        if self.server:
            self.should_shutdown = True
            self.server.should_exit = True
            
            # Give time for graceful shutdown
            await asyncio.sleep(1)
            
            logger.info("Service shutdown complete")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # On Windows, also handle CTRL+BREAK
        if sys.platform == "win32":
            signal.signal(signal.SIGBREAK, signal_handler)
    
    def _log_startup_info(self):
        """Log service startup information."""
        protocol = "https" if settings.ssl_enabled else "http"
        base_url = f"{protocol}://{settings.AGENT_HOST}:{settings.AGENT_PORT}"
        
        logger.info("=" * 60)
        logger.info("ATS RESUME REVIEWER AGENT - SERVICE STARTED")
        logger.info("=" * 60)
        logger.info(f"🚀 Service URL: {base_url}")
        logger.info(f"📊 Health Check: {base_url}/health")
        logger.info(f"📖 API Docs: {base_url}/docs" if settings.is_development else "📖 API Docs: Disabled in production")
        logger.info(f"🔄 Environment: {settings.AGENT_ENV}")
        logger.info(f"📝 Log Level: {settings.PYTHON_LOG_LEVEL}")
        logger.info(f"💾 Storage: {'PostgreSQL' if not settings.USE_INMEMORY_SAVER else 'In-Memory'}")
        logger.info(f"🔒 SSL: {'Enabled' if settings.ssl_enabled else 'Disabled'}")
        logger.info(f"📊 Langfuse: {'Enabled' if settings.langfuse_enabled else 'Disabled'}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("📡 Available Endpoints:")
        logger.info(f"  POST {base_url}/v1/stream        - Stream ATS analysis")
        logger.info(f"  POST {base_url}/v1/analyze       - Synchronous analysis")
        logger.info(f"  GET  {base_url}/v1/history/{{id}} - Conversation history")
        logger.info(f"  POST {base_url}/v1/feedback      - Submit feedback")
        logger.info("")
        logger.info("🔧 Service ready to accept requests")
        logger.info("=" * 60)


async def main():
    """Main entry point for the service."""
    service = ATSAgentService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)
    finally:
        await service.shutdown()


def run_service():
    """Run the ATS Agent service (synchronous entry point)."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service interrupted")
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_service()