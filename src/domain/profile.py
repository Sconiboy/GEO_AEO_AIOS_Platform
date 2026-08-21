"""
Subject & Competitor Profile Domain Contracts (Sprint 7.1)
Defines immutable profiles for client domain ownership, category offering, geography,
and declared competitor profiles. Eliminates inferring ownership from collection allowlists.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ClientProfile(BaseModel):
    """
    Explicit profile describing client identity and owned domains.
    """

    model_config = {"frozen": True}

    entity_name: str = Field(..., min_length=2, description="Client entity or organization name")
    client_domain: str = Field(..., min_length=3, description="Primary client domain (e.g. python.org)")
    owned_domains: List[str] = Field(..., min_length=1, description="List of all client-owned domains and subdomains")
    offering_category: str = Field(..., min_length=2, description="Category of offering or software product")
    geography: str = Field(default="Global", description="Target geographical market scope")


class CompetitorProfile(BaseModel):
    """
    Explicit profile describing a declared competitor and their owned domains.
    """

    model_config = {"frozen": True}

    competitor_entity_name: str = Field(..., min_length=2, description="Competitor organization or brand name")
    competitor_domains: List[str] = Field(..., min_length=1, description="List of competitor-owned domains")


class SubjectProfile(BaseModel):
    """
    Immutable subject profile containing client profile and declared competitor profiles.
    Used by ForensicGapAnalyzer to strictly classify domain ownership and relationships.
    """

    model_config = {"frozen": True}

    profile_id: str = Field(..., description="Unique profile identifier")
    client_profile: ClientProfile = Field(..., description="Explicit client profile")
    competitor_profiles: List[CompetitorProfile] = Field(default_factory=list, description="Declared competitor profiles")
