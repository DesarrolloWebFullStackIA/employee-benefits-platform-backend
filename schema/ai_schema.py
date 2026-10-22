from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthBlock(BaseModel):
    """Overall budget solvency metrics and qualitative executive summary."""
    status: str = Field(
        default="optimal",
        description="Health status: optimal (<=33% cap), warning (33-66%), critical (>66%)"
    )
    spent: float = Field(default=0.0, description="Total amount consumed to date")
    limit: float = Field(default=0.0, description="Total assigned budget limit")
    available: float = Field(default=0.0, description="Remaining available balance")
    ratio: float = Field(default=0.0, description="Consumption ratio percentage (0-100)")
    summaryText: str = Field(
        default="",
        description="Context-aware executive summary describing budget health"
    )


class AlertBlock(BaseModel):
    """Budget limit and semaphore threshold alerts (>66% cap or warning 33-66%)."""
    id: str = Field(..., description="Unique alert identifier")
    type: str = Field(default="category", description="Alert target type: 'category' or 'employee'")
    name: str = Field(..., description="Entity name reaching budget limit")
    percentage: float = Field(..., description="Percentage of assigned cap consumed")
    metric: str = Field(..., description="Formatted string showing spent vs assigned")
    severity: str = Field(
        default="warning",
        description="Alert severity level: 'optimal', 'warning', or 'critical'"
    )


class RecommendationBlock(BaseModel):
    """Strategic HR optimization and rebalancing recommendations."""
    summaryText: str = Field(
        default="",
        description="Actionable strategic recommendation for HR administrators"
    )
    underutilized: List[str] = Field(
        default_factory=list,
        description="Categories in safe zone (<=33% consumed)"
    )
    saturated: List[str] = Field(
        default_factory=list,
        description="Categories in red saturation zone (>66% consumed)"
    )


class BudgetInsightsResponse(BaseModel):
    """Structured 3-part AI budget diagnosis contract (US-INT-10.3 / CA-INT-10.4)."""
    success: bool = Field(default=True, description="Whether the insights were generated successfully")
    source: str = Field(
        default="google-genkit-advisor-v1",
        description="Inference source: Google Genkit Gemini model or fallback heuristic engine"
    )
    timestamp: str = Field(..., description="ISO 8601 generation timestamp")
    health: HealthBlock
    alerts: List[AlertBlock] = Field(default_factory=list)
    recommendations: RecommendationBlock


class BudgetInsightsRequest(BaseModel):
    """Request payload containing optional client store metrics and currency."""
    metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional pre-aggregated metrics from the frontend store"
    )
    currency: Optional[str] = Field(
        default="EUR",
        description="Currency code for formatting text (EUR or MXN)"
    )


class StructuredGenkitDiagnosis(BaseModel):
    """Target output schema for Google Genkit Gemini LLM structured generation."""
    health_status: str = Field(
        description="Overall status: 'optimal', 'warning', or 'critical'"
    )
    health_summary: str = Field(
        description="Executive financial summary paragraph in Spanish for HR managers"
    )
    recommendation_summary: str = Field(
        description="Actionable reallocation recommendations in Spanish"
    )
    underutilized_categories: List[str] = Field(
        default_factory=list,
        description="List of underutilized category names"
    )
    saturated_categories: List[str] = Field(
        default_factory=list,
        description="List of saturated category names nearing the budget limit"
    )

