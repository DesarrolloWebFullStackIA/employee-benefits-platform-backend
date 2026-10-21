from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: str
    color: str
    budget: Optional[float] = Field(default=0.0, ge=0, description="Suggested limit/budget cap for this category")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("The category name cannot be empty")
        return value


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    budget: Optional[float] = Field(None, ge=0)
    active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("The category name cannot be empty")
        return value


class CategoryResponse(CategoryBase):
    id: int
    active: bool = True
    created_at: datetime
    benefits_count: Optional[int] = None
    expenses_count: Optional[int] = None
    spent_amount: Decimal = Decimal("0.00")

    model_config = ConfigDict(from_attributes=True)
