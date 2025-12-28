"""Pydantic models for the Expert Agent."""

from typing import Optional
from pydantic import BaseModel, Field


class ExpertAgentResponse(BaseModel):
    """Structured response from the Expert Agent.

    On first invocation (paper ingestion), title and description are populated.
    On subsequent queries, only answer is populated.
    """

    title: Optional[str] = Field(
        default=None,
        description="Paper title. Only provided on first message when ingesting the paper."
    )
    description: Optional[str] = Field(
        default=None,
        description="Brief summary of paper's scope. Only provided on first message."
    )
    answer: Optional[str] = Field(
        default=None,
        description="Response to the user's question about the paper."
    )