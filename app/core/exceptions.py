"""Custom exceptions for RAS application."""
from typing import Any, Dict, Optional


class RASException(Exception):
    """Base exception for RAS application."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    retryable: bool = False
    user_message: str = "An unexpected error occurred"

    def __init__(self, message: str, **context):
        self.message = message
        self.context = context
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "context": self.context
        }


# =============================================================================
# Paper Errors
# =============================================================================

class PaperNotFoundError(RASException):
    """Paper does not exist in storage."""

    status_code = 404
    error_code = "PAPER_NOT_FOUND"
    retryable = False
    user_message = "The requested paper could not be found"

    def __init__(self, paper_id: str, source: str = "S3"):
        super().__init__(
            f"Paper not found: {paper_id}",
            paper_id=paper_id,
            source=source
        )
        self.paper_id = paper_id


class PaperParseError(RASException):
    """Failed to parse paper content."""

    status_code = 500
    error_code = "PAPER_PARSE_ERROR"
    retryable = False
    user_message = "Failed to process paper content"

    def __init__(self, paper_id: str, reason: str):
        super().__init__(
            f"Failed to parse paper {paper_id}: {reason}",
            paper_id=paper_id,
            reason=reason
        )
        self.paper_id = paper_id


# =============================================================================
# Agent Errors
# =============================================================================

class AgentError(RASException):
    """Base class for agent errors."""

    error_code = "AGENT_ERROR"
    user_message = "An error occurred while processing your request"

    def __init__(self, message: str, agent: str, **context):
        super().__init__(message, agent=agent, **context)
        self.agent = agent


class ExpertNotFoundError(AgentError):
    """Expert for a paper does not exist in registry."""

    status_code = 404
    error_code = "EXPERT_NOT_FOUND"
    retryable = False
    user_message = "Expert for this paper is not available"

    def __init__(self, paper_id: str):
        super().__init__(
            f"Expert not found for paper: {paper_id}",
            agent="expert",
            paper_id=paper_id
        )
        self.paper_id = paper_id


class ExpertQueryError(AgentError):
    """Expert failed to process query."""

    status_code = 500
    error_code = "EXPERT_QUERY_ERROR"
    retryable = True
    user_message = "Failed to get response from paper expert"

    def __init__(self, thread_id: str, reason: str):
        super().__init__(
            f"Expert query failed: {reason}",
            agent="expert",
            thread_id=thread_id,
            reason=reason
        )
        self.thread_id = thread_id


class ExpertCreationError(AgentError):
    """Failed to create expert for a paper."""

    status_code = 500
    error_code = "EXPERT_CREATION_ERROR"
    retryable = True
    user_message = "Failed to initialize paper expert"

    def __init__(self, paper_id: str, reason: str):
        super().__init__(
            f"Failed to create expert for paper {paper_id}: {reason}",
            agent="expert",
            paper_id=paper_id,
            reason=reason
        )
        self.paper_id = paper_id


# =============================================================================
# Retrieval Errors
# =============================================================================

class RetrievalError(RASException):
    """Base class for retrieval errors."""

    error_code = "RETRIEVAL_ERROR"
    user_message = "Failed to search knowledge base"

    def __init__(self, message: str, **context):
        super().__init__(message, **context)


class RetrievalServiceError(RetrievalError):
    """Retrieval service (Pinecone) is unavailable."""

    status_code = 503
    error_code = "RETRIEVAL_SERVICE_ERROR"
    retryable = True
    user_message = "Search service is temporarily unavailable"

    def __init__(self, reason: str):
        super().__init__(
            f"Retrieval service error: {reason}",
            reason=reason
        )


# =============================================================================
# LLM Errors
# =============================================================================

class LLMError(RASException):
    """Base class for LLM errors."""

    error_code = "LLM_ERROR"
    user_message = "AI service error"

    def __init__(self, message: str, agent: str, **context):
        super().__init__(message, agent=agent, **context)
        self.agent = agent


class LLMTimeoutError(LLMError):
    """LLM request timed out."""

    status_code = 504
    error_code = "LLM_TIMEOUT"
    retryable = True
    user_message = "Request timed out, please try again"

    def __init__(self, agent: str, timeout_seconds: float):
        super().__init__(
            f"LLM timeout after {timeout_seconds}s",
            agent=agent,
            timeout_seconds=timeout_seconds
        )


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""

    status_code = 429
    error_code = "LLM_RATE_LIMIT"
    retryable = True
    user_message = "Service is busy, please try again shortly"

    def __init__(self, agent: str, retry_after: Optional[float] = None):
        super().__init__(
            f"Rate limit exceeded",
            agent=agent,
            retry_after=retry_after
        )
        self.retry_after = retry_after