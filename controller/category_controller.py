from typing import Dict, List, Optional

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
        "budget": float(category.budget or 0.0),
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
        "created_at": category.created_at,
    }


def get_categories(db: Session) -> List[Dict]:
    categories = (
        db.query(Category)
        .filter(Category.active.is_(True))
        .order_by(Category.id.asc())
        .all()
    )
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


def create_category(db: Session, category_in: CategoryCreate) -> Dict:
    _ensure_unique_name(db, category_in.name)
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
    db: Session, category_id: int, category_in: CategoryUpdate
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
