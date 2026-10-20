from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class DashboardStatsSchema(BaseModel):
    total_allocated: Decimal = Field(
        ge=0,
        description="Presupuesto total asignado a la empresa",
    )
    total_spent: Decimal = Field(
        ge=0,
        description="Importe total de gastos aprobados",
    )


class CategoryStatsSchema(BaseModel):
    category_id: int
    category_name: str
    total_allocated: Decimal = Field(
        ge=0,
        description="Presupuesto total asignado a la categoría",
    )
    total_spent: Decimal = Field(
        ge=0,
        description="Importe total de gastos aprobados de la categoría",
    )


class CategoryStatsListSchema(BaseModel):
    categories: list[CategoryStatsSchema]


class RecentEmployeeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    department: str
    max_budget: Decimal
    top_category_id: int | None = None
    top_category: str | None = None
    top_category_spent: Decimal = Decimal("0.00")
    top_category_allocated: Decimal = Decimal("0.00")
    top_category_remaining: Decimal = Decimal("0.00")

class RecentEmployeeListSchema(BaseModel):
    employees: list[RecentEmployeeSchema]