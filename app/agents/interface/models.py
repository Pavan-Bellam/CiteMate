"""Response models for the Interface Agent.

The Interface Agent uses structured output to return corrections and
fact verification results in a consistent format.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class InterfaceResponse(BaseModel):
    """Structured response from the Interface Agent.

    Three separate concerns:
    - grammar_corrections: Local grammar/style issues
    - logic_issues: Local logic/consistency problems
    - fact_questions: Claims needing literature verification (triggers Router)
    - fact_results: Verification results after Router returns
    """

    grammar_corrections: Optional[List[str]] = Field(
        default=None,
        description="Grammar, spelling, and style issues found in the paragraph."
    )
    logic_issues: Optional[List[str]] = Field(
        default=None,
        description="Logical inconsistencies, argument flow problems, contradictions with previous paragraphs."
    )
    fact_questions: Optional[List[str]] = Field(
        default=None,
        description="Questions to verify factual claims. Sent to Router for literature verification."
    )
    fact_results: Optional[List[str]] = Field(
        default=None,
        description="Results of fact verification. Set after Router returns with answers."
    )
