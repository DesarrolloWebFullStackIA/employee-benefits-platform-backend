from typing import Dict, List, Optional
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from model.benefit_model import Benefit
from model.category_model import Category
from model.expense_model import Expense
from schema.category_schema import CategoryCreate, CategoryUpdate


def _category_response(db: Session, category: Category) -> Dict:
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "icon": category.icon,
        "color": category.color,
        "budget": category.budget or 0,
        "active": category.active,
        "benefits_count": (
            db.query(func.count(Benefit.id))
            .filter(Benefit.category_id == category.id)
            .scalar()
        ),
        "expenses_count": (
            db.query(func.count(Expense.id))
            .filter(Expense.category_id == category.id)
            .scalar()
        ),
        "spent_amount": (
            db.query(func.coalesce(func.sum(Expense.amount), 0))
            .filter(
                Expense.category_id == category.id,
                func.upper(Expense.status).in_(["APPROVED", "APROBADO"]),
            )
            .scalar()
        ),
        "created_at": category.created_at,
    }


def get_categories(db: Session, include_inactive: bool = False) -> List[Dict]:
    query = db.query(Category)
    if not include_inactive:
        query = query.filter(Category.active.is_(True))
    categories = query.order_by(Category.id.asc()).all()
    return [_category_response(db, category) for category in categories]


def get_category(db: Session, category_id: int) -> Dict:
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} was not found",
        )
    return _category_response(db, category)


def _ensure_unique_name(
    db: Session, name: str, excluding_category_id: Optional[int] = None
) -> None:
    query = db.query(Category).filter(func.lower(Category.name) == name.lower())
    if excluding_category_id is not None:
        query = query.filter(Category.id != excluding_category_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with name '{name}' already exists",
        )


def _remaining_category_budget(db: Session, global_budget_cap: Decimal) -> Decimal:
    total_assigned = db.query(
        func.coalesce(func.sum(Category.budget), 0)
    ).scalar()
    return max(
        Decimal("0.00"),
        global_budget_cap - Decimal(str(total_assigned)),
    )


def create_category(
    db: Session,
    category_in: CategoryCreate,
    global_budget_cap: Decimal,
) -> Dict:
    _ensure_unique_name(db, category_in.name)
    if category_in.budget <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El presupuesto de la categoría debe ser mayor que cero.",
        )
    remaining_budget = _remaining_category_budget(db, global_budget_cap)
    if category_in.budget > remaining_budget:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"El presupuesto solicitado ({category_in.budget:.2f}) supera "
                f"el dinero restante ({remaining_budget:.2f})."
            ),
        )
    category = Category(**category_in.model_dump())
    db.add(category)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with name '{category_in.name}' already exists",
        ) from exc
    db.refresh(category)
    return _category_response(db, category)


def update_category(
    db: Session,
    category_id: int,
    category_in: CategoryUpdate,
    global_budget_cap: Decimal,
) -> Dict:
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} was not found",
        )

    updates = category_in.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is not None:
        _ensure_unique_name(
            db, updates["name"], excluding_category_id=category_id
        )
    if "budget" in updates and updates["budget"] is not None:
        budget_increase = max(
            Decimal("0.00"), updates["budget"] - (category.budget or Decimal("0.00"))
        )
        remaining_budget = _remaining_category_budget(db, global_budget_cap)
        if budget_increase > remaining_budget:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"El aumento solicitado ({budget_increase:.2f}) supera "
                    f"el dinero restante ({remaining_budget:.2f})."
                ),
            )
    for field, value in updates.items():
        if value is not None:
            setattr(category, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category with name '{category.name}' already exists",
        ) from exc
    db.refresh(category)
    return _category_response(db, category)


def delete_category(db: Session, category_id: int) -> None:
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category with ID {category_id} was not found",
        )

    has_benefits = (
        db.query(Benefit.id).filter(Benefit.category_id == category_id).first()
        is not None
    )
    has_expenses = (
        db.query(Expense.id).filter(Expense.category_id == category_id).first()
        is not None
    )
    if has_benefits or has_expenses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete category '{category.name}' because it has active "
                "benefit allocations or expenses linked to it "
                "(Referential Integrity)."
            ),
        )

    db.delete(category)
    db.commit()
