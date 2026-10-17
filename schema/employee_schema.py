from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EmployeeBase(BaseModel):
    """Base attributes for an Employee entity."""

    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="First name of the employee",
        examples=["Laura"],
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Last name of the employee",
        examples=["Gómez"],
    )
    email: EmailStr = Field(
        ...,
        description="Corporate unique email address",
        examples=["laura.gomez@empresa.com"],
    )
    department: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Assigned company department",
        examples=["IT"],
    )
    position: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Job position or title",
        examples=["Senior Cloud Architect"],
    )
    max_budget: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Configurable global maximum spending cap in EUR",
        examples=[Decimal("2500.00")],
    )


class EmployeeCreate(EmployeeBase):
    """Payload schema for creating a new Employee."""

    pass


class EmployeeUpdate(BaseModel):
    """Payload schema for updating an existing Employee's personal details."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    department: Optional[str] = Field(None, min_length=1, max_length=100)
    position: Optional[str] = Field(None, min_length=1, max_length=100)
    max_budget: Optional[Decimal] = Field(None, ge=Decimal("0.00"))


class EmployeeBudgetUpdate(BaseModel):
    """Payload schema dedicated to 1-click global budget modification (CA-BE-04.2)."""

    max_budget: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="New total assigned budget cap in EUR",
        examples=[Decimal("2000.00")],
    )


class EmployeeBenefitItem(BaseModel):
    """Summary representation of an employee's assigned category benefit."""

    id: int
    category_id: int
    category_name: Optional[str] = None
    category_icon: Optional[str] = None
    category_color: Optional[str] = None
    allocated_amount: Decimal
    spent_amount: Decimal
    available_amount: Decimal = Decimal("0.00")
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeExpenseItem(BaseModel):
    """Summary representation of an expense registered by the employee."""

    id: int
    category_id: int
    category_name: Optional[str] = None
    amount: Decimal
    description: str
    receipt_url: Optional[str] = None
    status: str
    expense_date: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeResponse(EmployeeBase):
    """Response schema for employee list and standard single view."""

    id: int
    total_allocated: Decimal = Field(
        default=Decimal("0.00"),
        description="Sum of all allocated category benefits",
    )
    total_spent: Decimal = Field(
        default=Decimal("0.00"),
        description="Sum of all confirmed or committed expenses",
    )
    available_budget: Decimal = Field(
        default=Decimal("0.00"),
        description="Remaining budget from max_budget cap (max_budget - total_spent)",
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeDetailResponse(EmployeeResponse):
    """Extended response schema including nested benefit allocations and historical expenses."""

    benefits: List[EmployeeBenefitItem] = Field(default_factory=list)
    expenses: List[EmployeeExpenseItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
