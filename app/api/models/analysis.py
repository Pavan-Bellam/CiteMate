"""Analysis API models."""

from typing import Optional
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request to analyze a paragraph."""
    paragraph: str = Field(..., min_length=1, description="The paragraph text to analyze")
    paragraph_index: int = Field(..., ge=0, description="Index of the paragraph (0-based)")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID to continue")
    is_update: bool = Field(False, description="Whether this is an update to a previously analyzed paragraph")


class AnalyzeResponse(BaseModel):
    """Response from paragraph analysis."""
    conversation_id: str
    paragraph_index: int
    grammar_corrections: list[str]
    logic_issues: list[str]
    fact_results: list[str]
    expert_count: int
