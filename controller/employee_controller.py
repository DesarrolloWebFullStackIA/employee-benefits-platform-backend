from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from model.benefit_model import Benefit
from model.category_model import Category
from model.employee_model import Employee
from model.expense_model import Expense
from schema.employee_schema import EmployeeCreate, EmployeeUpdate


def _compute_employee_metrics(employee: Employee) -> Dict[str, Decimal]:
    """Helper to compute aggregated allocated, spent, and available budget metrics."""
    total_allocated = sum(
        (b.allocated_amount for b in employee.benefits), Decimal("0.00")
    )
    total_spent = sum(
        (
            e.amount
            for e in employee.expenses
            if e.status in ["PENDING", "APPROVED"]
        ),
        Decimal("0.00"),
    )
    max_budget = employee.max_budget or Decimal("0.00")
    available_budget = max(Decimal("0.00"), max_budget - total_spent)

    return {
        "total_allocated": total_allocated,
        "total_spent": total_spent,
        "available_budget": available_budget,
    }


def _format_employee_dict(employee: Employee) -> Dict[str, Any]:
    """Format single employee with budget metrics for EmployeeResponse."""
    metrics = _compute_employee_metrics(employee)
    return {
        "id": employee.id,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "email": employee.email,
        "department": employee.department,
        "position": employee.position,
        "max_budget": employee.max_budget,
        "total_allocated": metrics["total_allocated"],
        "total_spent": metrics["total_spent"],
        "available_budget": metrics["available_budget"],
        "created_at": employee.created_at,
        "updated_at": employee.updated_at,
    }


def get_all_employees(db: Session) -> List[Dict[str, Any]]:
    """Retrieve all employees with calculated budget and spending metrics."""
    employees = (
        db.query(Employee)
        .options(
            selectinload(Employee.benefits),
            selectinload(Employee.expenses),
        )
        .order_by(Employee.id.asc())
        .all()
    )
    return [_format_employee_dict(emp) for emp in employees]


def get_employee_by_id(db: Session, employee_id: int) -> Dict[str, Any]:
    """Retrieve full employee details including category benefits and historical expenses."""
    employee = (
        db.query(Employee)
        .options(
            selectinload(Employee.benefits).selectinload(Benefit.category),
            selectinload(Employee.expenses).selectinload(Expense.category),
        )
        .filter(Employee.id == employee_id)
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Empleado con ID {employee_id} no encontrado",
        )

    metrics = _compute_employee_metrics(employee)

    # Format nested benefits with category metadata
    benefits_data = []
    for b in employee.benefits:
        allocated = b.allocated_amount or Decimal("0.00")
        spent = b.spent_amount or Decimal("0.00")
        available = max(Decimal("0.00"), allocated - spent)
        benefits_data.append(
            {
                "id": b.id,
                "category_id": b.category_id,
                "category_name": b.category.name if b.category else None,
                "category_icon": b.category.icon if b.category else None,
                "category_color": b.category.color if b.category else None,
                "allocated_amount": allocated,
                "spent_amount": spent,
                "available_amount": available,
                "updated_at": b.updated_at,
            }
        )

    # Format nested expenses with category name
    expenses_data = []
    for exp in employee.expenses:
        expenses_data.append(
            {
                "id": exp.id,
                "category_id": exp.category_id,
                "category_name": exp.category.name if exp.category else None,
                "amount": exp.amount,
                "description": exp.description,
                "receipt_url": exp.receipt_url,
                "status": exp.status,
                "expense_date": exp.expense_date,
                "created_at": exp.created_at,
            }
        )

    return {
        "id": employee.id,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "email": employee.email,
        "department": employee.department,
        "position": employee.position,
        "max_budget": employee.max_budget,
        "total_allocated": metrics["total_allocated"],
        "total_spent": metrics["total_spent"],
        "available_budget": metrics["available_budget"],
        "created_at": employee.created_at,
        "updated_at": employee.updated_at,
        "benefits": benefits_data,
        "expenses": expenses_data,
    }


def create_employee(db: Session, employee_in: EmployeeCreate) -> Dict[str, Any]:
    """Create a new employee validating unique email constraint."""
    existing = db.query(Employee).filter(Employee.email == employee_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un empleado con el correo electrónico '{employee_in.email}'",
        )

    new_emp = Employee(
        first_name=employee_in.first_name,
        last_name=employee_in.last_name,
        email=employee_in.email,
        department=employee_in.department,
        position=employee_in.position,
        max_budget=employee_in.max_budget,
    )
    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)

    return _format_employee_dict(new_emp)


def update_employee(
    db: Session, employee_id: int, employee_in: EmployeeUpdate
) -> Dict[str, Any]:
    """Update employee personal information."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Empleado con ID {employee_id} no encontrado",
        )

    # Validate email uniqueness if changed
    if employee_in.email and employee_in.email != employee.email:
        email_conflict = (
            db.query(Employee).filter(Employee.email == employee_in.email).first()
        )
        if email_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un empleado con el correo electrónico '{employee_in.email}'",
            )

    update_data = employee_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)

    return _format_employee_dict(employee)


def delete_employee(db: Session, employee_id: int) -> bool:
    """Delete employee by ID triggering cascading removal of associated benefits and expenses."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Empleado con ID {employee_id} no encontrado",
        )

    db.delete(employee)
    db.commit()
    return True


def update_employee_budget(
    db: Session, employee_id: int, new_max_budget: Decimal
) -> Dict[str, Any]:
    """Update employee's total assigned budget cap with validation of committed expenses (CA-BE-04.2)."""
    employee = (
        db.query(Employee)
        .options(
            selectinload(Employee.benefits),
            selectinload(Employee.expenses),
        )
        .filter(Employee.id == employee_id)
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Empleado con ID {employee_id} no encontrado",
        )

    # Calculate committed spending: SUM(expenses.amount) WHERE status IN ('PENDING', 'APPROVED') AND employee_id = :id
    spent_total_result = (
        db.query(func.coalesce(func.sum(Expense.amount), Decimal("0.00")))
        .filter(
            Expense.employee_id == employee_id,
            Expense.status.in_(["PENDING", "APPROVED"]),
        )
        .scalar()
    )
    spent_total = Decimal(str(spent_total_result))

    # Guard: new_max_budget cannot be lower than already committed spending
    if new_max_budget < spent_total:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"El nuevo Total Asignado (€{new_max_budget:.2f}) no puede ser inferior "
                f"al gasto ya comprometido por el empleado (€{spent_total:.2f})"
            ),
        )

    employee.max_budget = new_max_budget
    db.commit()
    db.refresh(employee)

    return _format_employee_dict(employee)

