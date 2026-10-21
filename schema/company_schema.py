
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CompanyBudgetSchema(BaseModel):
    global_budget: Decimal = Field(
        ge=0,
        decimal_places=2,
    )


class CompanySchema(CompanyBudgetSchema):
    model_config = ConfigDict(from_attributes=True)
    id: int
