from typing import List

from decimal import Decimal

from fastapi import APIRouter, Depends, Header, Path, Query, status
from sqlalchemy.orm import Session

from controller import category_controller
from database.database import get_db
from config.config_variables import settings
from schema.category_schema import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=List[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List all active categories",
)
def get_categories(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
):
    return category_controller.get_categories(db, include_inactive=include_inactive)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a category by ID",
)
def get_category(
    category_id: int = Path(..., description="Category ID", gt=0),
    db: Session = Depends(get_db),
):
    return category_controller.get_category(db, category_id)


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
)
def create_category(
    category_in: CategoryCreate,
    global_budget_cap: Decimal = Header(
        default=settings.CATEGORY_GLOBAL_BUDGET_CAP,
        alias="X-Global-Budget-Cap",
        gt=0,
    ),
    db: Session = Depends(get_db),
):
    return category_controller.create_category(db, category_in, global_budget_cap)


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a category",
)
def update_category(
    category_in: CategoryUpdate,
    category_id: int = Path(..., description="Category ID", gt=0),
    global_budget_cap: Decimal = Header(
        default=settings.CATEGORY_GLOBAL_BUDGET_CAP,
        alias="X-Global-Budget-Cap",
        gt=0,
    ),
    db: Session = Depends(get_db),
):
    return category_controller.update_category(
        db, category_id, category_in, global_budget_cap
    )


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a category without linked benefits or expenses",
)
def delete_category(
    category_id: int = Path(..., description="Category ID", gt=0),
    db: Session = Depends(get_db),
):
    category_controller.delete_category(db, category_id)
    return None
