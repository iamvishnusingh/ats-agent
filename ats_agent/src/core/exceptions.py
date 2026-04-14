"""Shared exceptions for the ATS agent core."""


class ATSAgentError(Exception):
    """Base exception for ATS Agent errors."""

    pass


class ATSAgentConfigError(ATSAgentError):
    """Configuration error for ATS Agent."""

    pass
