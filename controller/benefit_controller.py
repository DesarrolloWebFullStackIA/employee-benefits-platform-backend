from decimal import Decimal
from typing import Any, Dict, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from model.benefit_model import Benefit
from model.category_model import Category
from model.employee_model import Employee
from schema.benefit_schema import BenefitCreate, BenefitUpdate


def _format_benefit_dict(benefit: Benefit) -> Dict[str, Any]:
    """Format single Benefit model into standard response dictionary."""
    allocated = benefit.allocated_amount or Decimal("0.00")
    spent = benefit.spent_amount or Decimal("0.00")
    available = max(Decimal("0.00"), allocated - spent)

    return {
        "id": benefit.id,
        "employee_id": benefit.employee_id,
        "category_id": benefit.category_id,
        "category_name": benefit.category.name if benefit.category else None,
        "category_icon": benefit.category.icon if benefit.category else None,
        "category_color": benefit.category.color if benefit.category else None,
        "allocated_amount": allocated,
        "spent_amount": spent,
        "available_amount": available,
        "updated_at": benefit.updated_at,
    }


def get_benefits_by_employee(db: Session, employee_id: int) -> List[Dict[str, Any]]:
    """Retrieve all category benefits assigned to a specific employee."""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Empleado con ID {employee_id} no encontrado",
        )

    benefits = (
        db.query(Benefit)
        .options(selectinload(Benefit.category))
        .filter(Benefit.employee_id == employee_id)
        .order_by(Benefit.id.asc())
        .all()
    )
    return [_format_benefit_dict(b) for b in benefits]


def assign_benefit_to_employee(
    db: Session, employee_id: int, benefit_in: BenefitCreate
) -> Dict[str, Any]:
    """Assign a category benefit cup to an employee validating uniqueness and global budget cap."""
    employee = (
        db.query(Employee)
        .options(selectinload(Employee.benefits))
        .filter(Employee.id == employee_id)
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Empleado con ID {employee_id} no encontrado",
        )

    category = db.query(Category).filter(Category.id == benefit_in.category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categoría con ID {benefit_in.category_id} no encontrada",
        )

    # Validate composite uniqueness: one benefit per category per employee
    existing_benefit = (
        db.query(Benefit)
        .filter(
            Benefit.employee_id == employee_id,
            Benefit.category_id == benefit_in.category_id,
        )
        .first()
    )
    if existing_benefit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El empleado ya tiene asignada la categoría '{category.name}'",
        )

    # Validate global budget cap: sum(allocated_amounts) <= employee.max_budget
    current_allocated = sum(
        (b.allocated_amount for b in employee.benefits), Decimal("0.00")
    )
    new_total_allocated = current_allocated + benefit_in.allocated_amount
    if new_total_allocated > employee.max_budget:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"La suma asignada propuesta (€{new_total_allocated:.2f}) excede "
                f"el tope global máximo del empleado (€{employee.max_budget:.2f})"
            ),
        )

    new_benefit = Benefit(
        employee_id=employee_id,
        category_id=benefit_in.category_id,
        allocated_amount=benefit_in.allocated_amount,
        spent_amount=Decimal("0.00"),
    )
    db.add(new_benefit)
    db.commit()
    db.refresh(new_benefit)

    # Load category relation for output
    new_benefit.category = category
    return _format_benefit_dict(new_benefit)


def update_benefit_allocation(
    db: Session, benefit_id: int, benefit_in: BenefitUpdate
) -> Dict[str, Any]:
    """Update an existing category benefit cup validating committed expenses and global cap."""
    benefit = (
        db.query(Benefit)
        .options(
            selectinload(Benefit.employee).selectinload(Employee.benefits),
            selectinload(Benefit.category),
        )
        .filter(Benefit.id == benefit_id)
        .first()
    )
    if not benefit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Beneficio con ID {benefit_id} no encontrado",
        )

    spent = benefit.spent_amount or Decimal("0.00")
    if benefit_in.allocated_amount < spent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"La nueva asignación (€{benefit_in.allocated_amount:.2f}) no puede ser inferior "
                f"al monto ya consumido en esta categoría (€{spent:.2f})"
            ),
        )

    # Validate global budget cap against employee's other benefits
    other_allocated = sum(
        (
            b.allocated_amount
            for b in benefit.employee.benefits
            if b.id != benefit_id
        ),
        Decimal("0.00"),
    )
    new_total_allocated = other_allocated + benefit_in.allocated_amount
    if new_total_allocated > benefit.employee.max_budget:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"La suma asignada propuesta (€{new_total_allocated:.2f}) excede "
                f"el tope global máximo del empleado (€{benefit.employee.max_budget:.2f})"
            ),
        )

    benefit.allocated_amount = benefit_in.allocated_amount
    db.commit()
    db.refresh(benefit)

    return _format_benefit_dict(benefit)


def delete_benefit(db: Session, benefit_id: int) -> bool:
    """Delete a category benefit assignment ensuring no existing spending has occurred."""
    benefit = db.query(Benefit).filter(Benefit.id == benefit_id).first()
    if not benefit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Beneficio con ID {benefit_id} no encontrado",
        )

    if (benefit.spent_amount or Decimal("0.00")) > Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No se puede eliminar un beneficio que ya cuenta con gastos consumidos",
        )

    db.delete(benefit)
    db.commit()
    return True
