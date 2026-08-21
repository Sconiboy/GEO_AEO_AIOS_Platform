"""
Query-Map, Source Scope, and Collection Policy Profile Domain Contracts
"""

from typing import List, Optional, Set
from pydantic import BaseModel, Field, field_validator

from .enums import HumanApprovalState, QueryIntent


class TargetQuery(BaseModel):
    """
    Represents a specific target buyer query mapped for generative engine evaluation.
    """

    query_id: str = Field(..., description="Unique query identifier")
    text: str = Field(..., min_length=5, description="The target buyer query text")
    intent: QueryIntent = Field(..., description="Intent classification")
    rationale: str = Field(..., min_length=10, description="Why this query matters to target buyers")
    approval_state: HumanApprovalState = Field(
        default=HumanApprovalState.PROPOSED,
        description="Governance approval state",
    )


class SourceScope(BaseModel):
    """
    Explicit domain whitelist and source boundary constraints.
    """

    scope_id: str = Field(..., description="Unique scope identifier")
    allowed_domains: List[str] = Field(
        ..., min_length=1, description="Curated list of pre-approved public domains"
    )
    blocked_domains: List[str] = Field(
        default_factory=list, description="Explicitly blocked domain list"
    )
    max_sources_per_query: int = Field(default=5, ge=1, le=20)

    @field_validator("allowed_domains")
    @classmethod
    def clean_domains(cls, v: List[str]) -> List[str]:
        cleaned = [d.strip().lower() for d in v if d.strip()]
        if not cleaned:
            raise ValueError("allowed_domains cannot be empty.")
        return cleaned


class CollectionPolicyProfile(BaseModel):
    """
    Operator-defined collection policy profile per query map run.
    """

    profile_id: str = Field(..., description="Unique profile identifier")
    allowed_schemes: Set[str] = Field(
        default_factory=lambda: {"https"},
        description="Allowed URI schemes (default: https only)",
    )
    max_redirects: int = Field(default=3, ge=0, le=10)
    max_response_bytes: int = Field(
        default=5 * 1024 * 1024, ge=1024, description="Maximum payload size in bytes"
    )
    timeout_seconds: float = Field(default=10.0, ge=0.5, le=60.0)
    source_scope: SourceScope = Field(..., description="Bound source scope rules")


class QueryMap(BaseModel):
    """
    Master QueryMap defining entity, category, persona, policy profile, and target queries.
    """

    query_map_id: str = Field(..., description="Unique QueryMap identifier")
    entity_name: str = Field(..., description="Entity or candidate product name")
    category: str = Field(..., description="Product/service market category")
    target_buyer_persona: str = Field(..., description="Target buyer persona description")
    geography: str = Field(default="US-Midwest", description="Target geographical region")
    locale: str = Field(default="en-US", description="Language locale")
    policy_profile: CollectionPolicyProfile = Field(..., description="Collection policy profile")
    queries: List[TargetQuery] = Field(
        ..., min_length=1, description="Mapped target buyer queries"
    )
