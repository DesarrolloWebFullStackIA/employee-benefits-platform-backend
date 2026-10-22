from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BenefitBase(BaseModel):
    """Base schema for category benefit allocation."""

    category_id: int = Field(
        ...,
        gt=0,
        description="ID of the benefit category to assign",
        examples=[1],
    )
    allocated_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Allocated spending cap for this category in EUR",
        examples=[Decimal("250.00")],
    )


class BenefitCreate(BenefitBase):
    """Payload schema for assigning a benefit to an employee."""

    pass


class BenefitUpdate(BaseModel):
    """Payload schema for modifying an allocated benefit amount."""

    allocated_amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Updated allocated budget for this benefit in EUR",
        examples=[Decimal("350.00")],
    )


class BenefitResponse(BaseModel):
    """Response schema for benefit allocations."""

    id: int
    employee_id: int
    category_id: int
    category_name: Optional[str] = None
    category_icon: Optional[str] = None
    category_color: Optional[str] = None
    allocated_amount: Decimal
    spent_amount: Decimal
    available_amount: Decimal = Decimal("0.00")
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
