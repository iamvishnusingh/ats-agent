"""FastAPI application setup for the ATS Agent.

This module configures the FastAPI application with all routes,
middleware, exception handlers, and enterprise features.
"""

from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import time

from ats_agent.src.core.agent import initialize_database
from ats_agent.src.routes import health, stream, history, feedback
from ats_agent.src.settings import settings
from ats_agent.src.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks."""
    # Startup
    logger.info("Starting ATS Resume Reviewer Agent")
    
    try:
        # Initialize database if using PostgreSQL
        await initialize_database()
        logger.info("Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down ATS Resume Reviewer Agent")
        # Add cleanup tasks here if needed


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    # Create FastAPI app
    app = FastAPI(
        title="ATS Resume Reviewer Agent",
        description="Advanced ATS Resume Analysis and Optimization Service",
        version="1.0.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        openapi_url="/openapi.json" if settings.is_development else None,
        lifespan=lifespan
    )
    
    # Configure middleware
    setup_middleware(app)
    
    # Register routes
    register_routes(app)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Configure OpenAPI
    setup_openapi(app)
    
    logger.info("FastAPI application created and configured")
    
    return app


def setup_middleware(app: FastAPI) -> None:
    """Configure application middleware.
    
    Args:
        app: FastAPI application instance
    """
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )
    
    # Compression middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests
        if process_time > 5.0:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {process_time:.2f}s"
            )
        
        return response
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} "
                f"in {process_time:.2f}s"
            )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"after {process_time:.2f}s - {str(e)}"
            )
            raise


def register_routes(app: FastAPI) -> None:
    """Register all application routes.
    
    Args:
        app: FastAPI application instance
    """
    # Health check routes
    app.include_router(health.router)
    
    # Streaming analysis routes
    app.include_router(stream.router)
    
    # Conversation history routes  
    app.include_router(history.router)
    
    # Feedback routes
    app.include_router(feedback.router)
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with service information."""
        return {
            "service": "ATS Resume Reviewer Agent",
            "version": "1.0.0",
            "description": "Advanced ATS Resume Analysis and Optimization Service",
            "docs": "/docs" if settings.is_development else "Documentation not available in production",
            "health": "/health",
            "endpoints": {
                "report": "/v1/report",
                "streaming": "/v1/stream",
                "analysis": "/v1/analyze",
                "history": "/v1/history/{thread_id}",
                "feedback": "/v1/feedback",
            }
        }
    
    logger.info("Application routes registered")


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup global exception handlers.
    
    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with structured error responses."""
        logger.error(f"HTTP {exc.status_code}: {exc.detail}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": f"HTTP {exc.status_code}",
                "message": exc.detail,
                "path": str(request.url.path),
                "method": request.method,
                "timestamp": time.time()
            }
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle value errors as bad requests."""
        logger.error(f"ValueError: {str(exc)}")
        
        return JSONResponse(
            status_code=400,
            content={
                "error": "Validation Error",
                "message": str(exc),
                "path": str(request.url.path),
                "timestamp": time.time()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions as internal server errors."""
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred" if settings.is_production else str(exc),
                "path": str(request.url.path),
                "timestamp": time.time()
            }
        )


def setup_openapi(app: FastAPI) -> None:
    """Configure OpenAPI documentation.
    
    Args:
        app: FastAPI application instance
    """
    if not settings.is_development:
        return
    
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title="ATS Resume Reviewer Agent API",
            version="1.0.0",
            description="""
            ## Advanced ATS Resume Analysis Service
            
            This API provides comprehensive ATS (Applicant Tracking System) resume analysis
            with real-time streaming capabilities and enterprise features.
            
            ### Key Features
            - **Real-time Streaming**: Server-Sent Events for live analysis feedback
            - **Comprehensive Analysis**: Keyword matching, skills gap analysis, ATS scoring
            - **Conversation Management**: Multi-turn conversations with thread persistence
            - **Enterprise Ready**: Health checks, feedback collection, observability
            
            ### Usage Examples
            
            #### Stream Analysis
            ```bash
            curl -X POST "http://localhost:8082/v1/stream" \\
              -H "Content-Type: application/json" \\
              -d '{
                "resume_text": "Your resume content...",
                "job_description": "Job requirements...",
                "stream_tokens": true
              }'
            ```
            
            #### One-shot report (text or URLs)
            ```bash
            curl -X POST "http://localhost:8082/v1/report" \\
              -H "Content-Type: application/json" \\
              -d '{
                "resume_url": "https://example.com/me.pdf",
                "job_description_url": "https://example.com/job.html"
              }'
            ```

            #### Synchronous Analysis
            ```bash
            curl -X POST "http://localhost:8082/v1/analyze" \\
              -H "Content-Type: application/json" \\
              -d '{
                "resume_text": "Your resume content...",
                "job_description": "Job requirements..."
              }'
            ```
            """,
            routes=app.routes,
        )
        
        # Add additional OpenAPI customizations
        openapi_schema["info"]["contact"] = {
            "name": "ATS Agent Support",
            "email": "support@atsagent.com"
        }
        
        openapi_schema["info"]["license"] = {
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html"
        }
        
        # Add security schemes if authentication is implemented
        # openapi_schema["components"]["securitySchemes"] = {
        #     "bearerAuth": {
        #         "type": "http",
        #         "scheme": "bearer",
        #         "bearerFormat": "JWT"
        #     }
        # }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi


# Create the FastAPI application
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "ats_agent.src.api:app",
        host=settings.AGENT_HOST,
        port=settings.AGENT_PORT,
        reload=settings.is_development,
        log_level=settings.PYTHON_LOG_LEVEL.lower(),
        ssl_keyfile=settings.AGENT_SSL_KEYFILE,
        ssl_certfile=settings.AGENT_SSL_CERTFILE
    )