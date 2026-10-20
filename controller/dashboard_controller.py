from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from model.employee_model import Employee
from model.expense_model import Expense
from model.category_model import Category
from model.benefit_model import Benefit
from model.company_model import Company


def get_dashboard_stats(db: Session) -> dict:
    total_allocated = (
    db.query(Company.global_budget)
    .order_by(Company.id.asc())
    .first()
    )
    total_allocated = (
    total_allocated[0]
    if total_allocated is not None
    else Decimal("0.00")
    )
    
    # Sumar únicamente los gastos aprobados
    total_spent = (
        db.query(
            func.coalesce(
                func.sum(Expense.amount),
                Decimal("0.00"),
            )
        )
        .filter(Expense.status == "APPROVED")
        .scalar()
    )

    return {
        "total_allocated": total_allocated,
        "total_spent": total_spent,
    }



def get_recent_employees(db: Session) -> list[dict[str, Any]]:
    # 1. Obtener los cinco empleados más recientes
    employees = (
        db.query(Employee)
        .order_by(Employee.created_at.desc(), Employee.id.desc())
        .limit(5)
        .all()
    )

    if not employees:
        return []

    employee_ids = [employee.id for employee in employees]

    # 2. Sumar los gastos APROBADOS por empleado y categoría
    expense_rows = (
        db.query(
            Expense.employee_id.label("employee_id"),
            Expense.category_id.label("category_id"),
            Category.name.label("category_name"),
            func.sum(Expense.amount).label("total_spent"),
        )
        .join(Category, Category.id == Expense.category_id)
        .filter(
            Expense.employee_id.in_(employee_ids),
            Expense.status == "APPROVED",
        )
        .group_by(
            Expense.employee_id,
            Expense.category_id,
            Category.name,
        )
        .order_by(
            Expense.employee_id.asc(),
            func.sum(Expense.amount).desc(),
            Expense.category_id.asc(),
        )
        .all()
    )

    # 3. Seleccionar la categoría con mayor gasto de cada empleado.
    # En caso de empate, gana la categoría con menor ID.
    top_categories = {}

    for row in expense_rows:
        if row.employee_id not in top_categories:
            top_categories[row.employee_id] = row

    # 4. Obtener los presupuestos asignados por categoría
    benefits = (
        db.query(Benefit)
        .filter(Benefit.employee_id.in_(employee_ids))
        .all()
    )

    benefits_by_key = {
        (benefit.employee_id, benefit.category_id): benefit
        for benefit in benefits
    }

    # 5. Construir la respuesta para el frontend
    result = []

    for employee in employees:
        top_category = top_categories.get(employee.id)

        category_name = None
        category_id = None
        category_spent = Decimal("0.00")
        category_allocated = Decimal("0.00")
        category_remaining = Decimal("0.00")

        if top_category is not None:
            category_id = top_category.category_id
            category_name = top_category.category_name
            category_spent = top_category.total_spent or Decimal("0.00")

            benefit = benefits_by_key.get(
                (employee.id, category_id)
            )

            if benefit is not None:
                category_allocated = (
                    benefit.allocated_amount or Decimal("0.00")
                )

            # El saldo disponible nunca se muestra como negativo.
            category_remaining = max(
                Decimal("0.00"),
                category_allocated - category_spent,
            )

        result.append({
            "id": employee.id,
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email,
            "department": employee.department,
            "max_budget": employee.max_budget,

            # Nuevos campos para el dashboard
            "top_category_id": category_id,
            "top_category": category_name,
            "top_category_spent": category_spent,
            "top_category_allocated": category_allocated,
            "top_category_remaining": category_remaining,
        })

    return result


def get_category_stats(db: Session) -> list[dict]:
    # Cumulative allocated budget by category
    allocated = (
        db.query(
            Benefit.category_id.label("category_id"),
            func.sum(Benefit.allocated_amount).label("total_allocated"),
        )
        .group_by(Benefit.category_id)
        .subquery()
    )

    #Accumulated approved expenses by category
    spent = (
        db.query(
            Expense.category_id.label("category_id"),
            func.sum(Expense.amount).label("total_spent"),
        )
        .filter(Expense.status == "APPROVED")
        .group_by(Expense.category_id)
        .subquery()
    )

    results = (
        db.query(
            Category.id,
            Category.name,
            func.coalesce(
                allocated.c.total_allocated, Decimal("0.00")
            ).label("total_allocated"),
            func.coalesce(
                spent.c.total_spent, Decimal("0.00")
            ).label("total_spent"),
        )
        .outerjoin(
            allocated,
            allocated.c.category_id == Category.id,
        )
        .outerjoin(
            spent,
            spent.c.category_id == Category.id,
        )
        .order_by(Category.created_at.desc(), Category.id.desc())
        .limit(5)
        .all()
    )

    return [
        {
            "category_id": row.id,
            "category_name": row.name,
            "total_allocated": row.total_allocated,
            "total_spent": row.total_spent,
        }
        for row in results
    ]