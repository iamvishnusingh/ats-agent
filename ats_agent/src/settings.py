"""Configuration settings for the ATS Agent.

This module handles environment variable loading and configuration
management for the ATS agent service.
"""

import os
from typing import Optional
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server Configuration
    AGENT_HOST: str = Field(default="0.0.0.0", description="Server host")
    AGENT_PORT: int = Field(default=8082, description="Server port")
    AGENT_ENV: str = Field(default="development", description="Environment")
    
    # Logging
    PYTHON_LOG_LEVEL: str = Field(default="INFO", description="Python log level")
    
    # Database Configuration
    POSTGRES_USER: str = Field(default="ats_user", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(default="ats_password", description="PostgreSQL password")
    POSTGRES_DB: str = Field(default="ats_agent", description="PostgreSQL database name")
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    
    # Storage
    USE_INMEMORY_SAVER: bool = Field(default=True, description="Use in-memory storage instead of PostgreSQL")
    
    # External Services / LLM
    # auto: OpenAI if OPENAI_API_KEY set, else Google if GOOGLE_API_KEY set, else Ollama (local)
    LLM_PROVIDER: str = Field(
        default="auto",
        description="auto | openai | google | ollama",
    )
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    GOOGLE_API_KEY: Optional[str] = Field(
        default=None,
        description="Google AI (Gemini) API key",
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    )
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL when LLM_PROVIDER=ollama or auto fallback",
    )
    OLLAMA_MODEL: str = Field(
        default="llama3.2",
        description="Ollama model tag (e.g. llama3.2, gemma2:2b)",
    )
    
    # Langfuse Configuration (Optional)
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(default=None, description="Langfuse public key")
    LANGFUSE_SECRET_KEY: Optional[str] = Field(default=None, description="Langfuse secret key")
    LANGFUSE_BASE_URL: Optional[str] = Field(default=None, description="Langfuse base URL")
    LANGFUSE_TRACING_ENVIRONMENT: str = Field(default="development", description="Langfuse environment")
    
    # SSL Configuration
    AGENT_SSL_KEYFILE: Optional[str] = Field(default=None, description="SSL private key file path")
    AGENT_SSL_CERTFILE: Optional[str] = Field(default=None, description="SSL certificate file path")
    
    # CORS Configuration
    CORS_ORIGINS: list = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, description="Maximum file upload size (10MB)")
    ALLOWED_EXTENSIONS: list = Field(
        default=["pdf", "docx", "doc", "txt"],
        description="Allowed file extensions"
    )
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Rate limit requests per minute")
    
    # Analysis Configuration
    DEFAULT_MODEL: str = Field(
        default="gpt-3.5-turbo",
        description="Model id for OpenAI/Google (e.g. gpt-4o-mini, gemini-2.0-flash)",
    )
    MAX_TOKENS: int = Field(default=4000, description="Maximum tokens for LLM responses")
    TEMPERATURE: float = Field(default=0.3, description="LLM temperature")
    
    # Cache Configuration
    ENABLE_CACHE: bool = Field(default=True, description="Enable response caching")
    CACHE_TTL: int = Field(default=3600, description="Cache TTL in seconds")

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @property
    def database_uri(self) -> str:
        """Get database connection URI."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_uri(self) -> str:
        """Get synchronous database connection URI."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.AGENT_ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.AGENT_ENV.lower() == "development"

    @property
    def langfuse_enabled(self) -> bool:
        """Check if Langfuse tracing is enabled."""
        return bool(self.LANGFUSE_PUBLIC_KEY and self.LANGFUSE_SECRET_KEY)

    @property
    def ssl_enabled(self) -> bool:
        """Check if SSL is configured."""
        return bool(self.AGENT_SSL_KEYFILE and self.AGENT_SSL_CERTFILE)

    def get_llm_config(self) -> dict:
        """Get LLM configuration."""
        config = {
            "model": self.DEFAULT_MODEL,
            "max_tokens": self.MAX_TOKENS,
            "temperature": self.TEMPERATURE,
        }
        
        if self.OPENAI_API_KEY:
            config["openai_api_key"] = self.OPENAI_API_KEY
        
        if self.GOOGLE_API_KEY:
            config["google_api_key"] = self.GOOGLE_API_KEY
            
        return config


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings