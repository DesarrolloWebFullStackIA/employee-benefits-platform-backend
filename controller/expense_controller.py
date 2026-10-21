from datetime import date as Date
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from model.benefit_model import Benefit
from model.category_model import Category
from model.employee_model import Employee
from model.expense_model import Expense
from services.cloudinary_service import upload_receipt

ACTIVE_STATUSES = ("pending", "approved")


def _to_dict(expense: Expense) -> dict:
    return {
        "id": expense.id,
        "date": expense.date.isoformat(),
        "employee": {
            "id": expense.employee.id,
            "name": f"{expense.employee.first_name} {expense.employee.last_name}",
            "role": getattr(expense.employee, "position", None) or "Empleado",
        },
        "category": expense.category.name,
        "concept": expense.concept,
        "amount": float(expense.amount),
        "receiptType": expense.receipt_type or "pdf",
        "receiptUrl": expense.receipt_url or "#",
        "status": expense.status,
        "rejectionReason": expense.rejection_reason,
    }

def _get_benefit(db: Session, employee_id: int, category_id: int, lock: bool = False) -> Optional[Benefit]:
    query = db.query(Benefit).filter(
        Benefit.employee_id == employee_id, Benefit.category_id == category_id
    )
    if lock:
        query = query.with_for_update()
    return query.first()

def _committed_amount(db: Session, employee_id: int, category_id: int, exclude_id: Optional[int] = None) -> Decimal:
    query = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
        Expense.employee_id == employee_id,
        Expense.category_id == category_id,
        Expense.status.in_(ACTIVE_STATUSES),
    )
    if exclude_id is not None:
        query = query.filter(Expense.id != exclude_id)
    return Decimal(str(query.scalar()))

def _available(db: Session, employee_id: int, category_id: int) -> Decimal:
    benefit = _get_benefit(db, employee_id, category_id)
    if benefit is None:
        return Decimal("0")
    return Decimal(str(benefit.allocated_amount)) - _committed_amount(db, employee_id, category_id)



def get_expenses(db: Session, status: str, employee_id: int, category_id: int, search: str):
    query = db.query(Expense).options(joinedload(Expense.employee), joinedload(Expense.category))
    if status:
        query = query.filter(Expense.status == status)
    if employee_id:
        query = query.filter(Expense.employee_id == employee_id)
    if category_id:
        query = query.filter(Expense.category_id == category_id)
    if search:
        like = f"%{search}%"
        query = query.join(Employee).filter(
            Employee.first_name.ilike(like) | 
            Employee.last_name.ilike(like) | 
            Expense.concept.ilike(like)
        )
    return [_to_dict(e) for e in query.order_by(Expense.date.desc(), Expense.id.desc()).all()]


def create_expense(db: Session, employee_id: int, category_id: int, concept: str, amount: float, date: Date, receipt: UploadFile):
    if amount <= 0:
        raise HTTPException(400, "El importe debe ser mayor que 0.")
    if not concept.strip():
        raise HTTPException(400, "El concepto es obligatorio.")
    if not db.get(Employee, employee_id) or not db.get(Category, category_id):
        raise HTTPException(404, "Empleado o categoría no encontrados.")

    try:
        benefit = _get_benefit(db, employee_id, category_id, lock=True)
        if benefit is None:
            raise HTTPException(400, "El empleado no tiene beneficio en esa categoría.")
        
        available = Decimal(str(benefit.allocated_amount)) - _committed_amount(db, employee_id, category_id)
        if Decimal(str(amount)) > available:
            raise HTTPException(409, f"Saldo insuficiente. Disponible: {available:.2f} €")

        receipt_url = None
        if receipt:
            receipt_url = upload_receipt(receipt)


        expense = Expense(
            employee_id=employee_id,
            category_id=category_id,
            concept=concept.strip(),
            amount=amount,
            date=date,
            status="pending",
            receipt_url=receipt_url,
            receipt_type="image" if receipt and (receipt.content_type or "").startswith("image/") else "pdf",
        )
        db.add(expense)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"No se pudo registrar el gasto: {str(e)}")

    db.refresh(expense)
    return _to_dict(expense)


def update_expense(db: Session, expense_id: int, employee_id: int, category_id: int, concept: str, amount: float, date: Date):
    if amount <= 0:
        raise HTTPException(400, "El importe debe ser mayor que 0.")
    if not concept.strip():
        raise HTTPException(400, "El concepto es obligatorio.")

    try:
        expense = db.query(Expense).filter(Expense.id == expense_id).with_for_update().first()
        if expense is None:
            raise HTTPException(404, "Gasto no encontrado.")
        if expense.status != "pending":
            raise HTTPException(409, "Solo se pueden editar gastos pendientes.")

        benefit = _get_benefit(db, employee_id, category_id, lock=True)
        if benefit is None:
            raise HTTPException(400, "El empleado no tiene beneficio en esa categoría.")
        
        others = _committed_amount(db, employee_id, category_id, exclude_id=expense.id)
        if others + Decimal(str(amount)) > Decimal(str(benefit.allocated_amount)):
            raise HTTPException(409, f"Saldo insuficiente para editar este gasto.")

        expense.employee_id = employee_id
        expense.category_id = category_id
        expense.concept = concept.strip()
        expense.amount = amount
        expense.date = date
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"No se pudo editar el gasto: {str(e)}")

    db.refresh(expense)
    return _to_dict(expense)


def approve_expense(db: Session, expense_id: int):
    try:
        expense = db.query(Expense).filter(Expense.id == expense_id).with_for_update().first()
        if expense is None:
            raise HTTPException(404, "Gasto no encontrado.")
        if expense.status != "pending":
            raise HTTPException(409, "Solo se pueden aprobar gastos pendientes.")

        benefit = _get_benefit(db, expense.employee_id, expense.category_id, lock=True)
        if benefit is None:
            raise HTTPException(400, "El empleado ya no tiene beneficio en esa categoría.")
        
        others = _committed_amount(db, expense.employee_id, expense.category_id, exclude_id=expense.id)
        if others + Decimal(str(expense.amount)) > Decimal(str(benefit.allocated_amount)):
            raise HTTPException(409, "Saldo insuficiente para aprobar este gasto.")

        expense.status = "approved"
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"No se pudo aprobar el gasto: {str(e)}")

    db.refresh(expense)
    return _to_dict(expense)


def reject_expense(db: Session, expense_id: int, reason: str):
    if not reason.strip():
        raise HTTPException(400, "El motivo del rechazo es obligatorio.")
    try:
        expense = db.query(Expense).filter(Expense.id == expense_id).with_for_update().first()
        if expense is None:
            raise HTTPException(404, "Gasto no encontrado.")
        if expense.status != "pending":
            raise HTTPException(409, "Solo se pueden rechazar gastos pendientes.")

        expense.status = "rejected"
        expense.rejection_reason = reason.strip()
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"No se pudo rechazar el gasto: {str(e)}")

    db.refresh(expense)
    return _to_dict(expense)


def get_balance(db: Session, employee_id: int, category_id: int):
    return {"available": float(_available(db, employee_id, category_id))}


def list_categories(db: Session):
    categories = db.query(Category).all()
    return [{"id": c.id, "name": c.name} for c in categories]

def delete_expense(db: Session, expense_id: int):
    try:
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if expense is None:
            raise HTTPException(404, "Gasto no encontrado.")

        if expense.status == "approved":
            raise HTTPException(409, "No se puede eliminar un gasto aprobado.")

        db.delete(expense)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"No se pudo eliminar el gasto: {str(e)}")
    
    return {"success": True, "message": "Gasto eliminado correctamente"}