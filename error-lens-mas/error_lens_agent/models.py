"""Pydantic models for structured output across ErrorLens agents."""

from enum import Enum
from pydantic import BaseModel, Field


class SourceType(str, Enum):
    GCP_DOCS  = "gcp_docs"
    COMMUNITY = "community"
    COMBINED  = "gcp_docs + community"
    UNKNOWN   = "unknown"


class error_triage_result(BaseModel):
    """Structured output from the orchestrator's intent classification."""
    intent:                   str       = Field(description="Classified user intent for the current pipeline. Expected value: 'new_error'")
    error_message:            str       = Field(default="", description="The raw error message extracted from the user input")
    primary_service:          str       = Field(default="unknown", description="Primary GCP service most likely owning the incident (e.g. Cloud Run, GKE, BigQuery)")
    related_services:         list[str] = Field(default_factory=list, description="Additional GCP services involved in the incident, excluding primary_service")
    severity:                 str       = Field(default="medium", description="Estimated severity: low, medium, high, critical")
    docs_search_queries:      list[str] = Field(default_factory=list, description="2-3 optimised search queries for official GCP documentation and MCP lookup")
    community_search_queries: list[str] = Field(default_factory=list, description="2-3 optimised search queries for Stack Overflow, GitHub, Reddit, blogs, and community forums")


class research_hit(BaseModel):
    source:          SourceType = Field(description="Origin: gcp_docs | community | gcp_docs + community | unknown")
    title:           str        = Field(description="Title or heading of the result")
    snippet:         str        = Field(description="Relevant excerpt — max 100 words")
    url:             str        = Field(default="")
    relevance_score: float      = Field(default=0.5, ge=0.0, le=1.0)
    why_relevant:    str        = Field(default="")

    class Config:
        use_enum_values = True


class gcp_knowledge_research_result(BaseModel):
    """Structured output from the GCP Developer Knowledge agent."""
    hits:               list[research_hit] = Field(default_factory=list, description="Ranked list of GCP documentation hits")
    service_identified: str                = Field(default="", description="GCP service the docs relate to")
    summary:            str                = Field(default="", description="Brief synthesis of what the docs say about this error")


class community_research_result(BaseModel):
    """Structured output from the Web & Community Research agent."""
    hits:                list[research_hit] = Field(default_factory=list, description="Ranked list of community search hits")
    community_consensus: str                = Field(default="", description="Common resolution suggested across StackOverflow / Reddit / community posts")
    summary:             str                = Field(default="", description="Brief synthesis of web/community findings")


class ranked_fix(BaseModel):
    rank:              int        = Field(description="Position in ranked list. 1 is highest.")
    title:             str        = Field(description="Short imperative title")
    steps:             list[str]  = Field(default_factory=list)
    source:            SourceType = Field(default=SourceType.UNKNOWN, description="Origin: gcp_docs | community | gcp_docs + community | unknown")
    source_url:        str        = Field(default="")
    confidence:        float      = Field(default=0.5, ge=0.0, le=1.0)
    why_recommended:   str        = Field(default="")
    supporting_sources: list[SourceType] = Field(default_factory=list)
    supporting_urls:   list[str]  = Field(default_factory=list)

    class Config:
        use_enum_values = True


class synthesis_result(BaseModel):
    """Structured output from the synthesis agent inside the quality loop."""
    root_cause:          str              = Field(default="", description="Plain English explanation of why this error occurred")
    ranked_fixes:        list[ranked_fix] = Field(default_factory=list, description="All fix options ranked by composite confidence, highest first")
    overall_confidence:  float            = Field(default=0.0, ge=0.0, le=1.0, description="Confidence of the top-ranked fix")
    sources_agreed:      bool             = Field(default=False, description="True if GCP docs and community sources align on the top fix")
    sources_contradicted: bool            = Field(default=False, description="True if sources recommend conflicting approaches")
    fallback_guidance:   str              = Field(default="", description="What to investigate if all ranked fixes fail")


class kb_record_input(BaseModel):
    """Structured input for recording a new error into the knowledge bank."""
    error_message:      str = Field(description="The raw error message verbatim")
    error_summary:      str = Field(description="One-sentence normalized summary of the error")
    gcp_service:        str = Field(description="Primary GCP service (e.g. Cloud Run, BigQuery)")
    severity:           str = Field(description="One of: low, medium, high, critical")
    root_cause:         str = Field(description="Explanation of why the error occurred")
    suggested_fixes:    str = Field(description="Full synthesis_result serialized as a compact JSON string")
    overall_confidence: str = Field(description="Confidence score 0.0-1.0 as decimal string, e.g. '0.87'")
    project_id:         str = Field(description="GCP project ID from the orchestrator")


class kb_record_result(BaseModel):
    """Structured output from the knowledge bank recorder agent."""
    case_ref: str = Field(description="Human-friendly case reference (e.g. EL-20260413-00001) of the newly recorded case")


class kb_resolve_result(BaseModel):
    """Structured output from the knowledge bank resolve agent."""
    case_ref:      str = Field(description="Human-friendly case reference of the resolved case (e.g. EL-20260413-00001)")
    gcp_service:   str = Field(default="", description="GCP service of the resolved case")
    status:        str = Field(default="resolved", description="New status of the case")
    confirmed_fix: str = Field(default="", description="The fix that resolved the issue")
    resolved_at:   str = Field(default="", description="Timestamp when the case was resolved")