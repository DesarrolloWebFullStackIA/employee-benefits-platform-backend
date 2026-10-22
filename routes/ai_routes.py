from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from controller import ai_controller
from database.database import get_db
from schema.ai_schema import BudgetInsightsRequest, BudgetInsightsResponse

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post(
    "/insights",
    response_model=BudgetInsightsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI budget health diagnosis and optimization recommendations",
    description=(
        "Analyzes real-time employee and category spending against assigned caps using "
        "Google Genkit and Gemini LLM. Emits a structured 3-part diagnosis with overall health, "
        "threshold alerts (>85% cap), and HR strategic reallocation advice."
    ),
)
async def get_budget_insights(
    request: Optional[BudgetInsightsRequest] = None,
    db: Session = Depends(get_db),
):
    """Generate structured AI budget insights for the HR Executive Dashboard (US-INT-10.4)."""
    return await ai_controller.generate_budget_insights(request=request, db=db)
