from datetime import date as Date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Path, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from controller import expense_controller
from database.database import get_db

router = APIRouter(prefix="/expenses", tags=["Expenses"])

class RejectBody(BaseModel):
    reason: str


@router.get("", status_code=status.HTTP_200_OK, summary="List expenses")
@router.get("/", status_code=status.HTTP_200_OK, include_in_schema=False)
def list_expenses(
    status: Optional[str] = Query(None, pattern="^(?i)(pending|approved|rejected)$"),
    employee_id: Optional[int] = None,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return expense_controller.get_expenses(db, status, employee_id, category_id, search)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create a new expense")
@router.post("/", status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_expense(
    employee_id: int = Form(..., alias="employeeId"),
    category_id: int = Form(..., alias="categoryId"),
    concept: str = Form(...),
    amount: float = Form(...),
    date: Date = Form(...),
    receipt: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    return expense_controller.create_expense(db, employee_id, category_id, concept, amount, date, receipt)


@router.put("/{expense_id}", status_code=status.HTTP_200_OK, summary="Update an expense")
def update_expense(
    expense_id: int = Path(..., gt=0),
    employee_id: int = Form(..., alias="employeeId"),
    category_id: int = Form(..., alias="categoryId"),
    concept: str = Form(...),
    amount: float = Form(...),
    date: Date = Form(...),
    db: Session = Depends(get_db),
):
    return expense_controller.update_expense(db, expense_id, employee_id, category_id, concept, amount, date)


@router.patch("/{expense_id}/approve", status_code=status.HTTP_200_OK, summary="Approve an expense")
def approve_expense(
    expense_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
):
    return expense_controller.approve_expense(db, expense_id)


@router.patch("/{expense_id}/reject", status_code=status.HTTP_200_OK, summary="Reject an expense")
def reject_expense(
    expense_id: int = Path(..., gt=0),
    body: RejectBody = ...,
    db: Session = Depends(get_db),
):
    return expense_controller.reject_expense(db, expense_id, body.reason)


@router.get("/categories", status_code=status.HTTP_200_OK, summary="List categories")
def list_categories(db: Session = Depends(get_db)):
    return expense_controller.list_categories(db)



@router.get("/employees/{employee_id}/balance", status_code=status.HTTP_200_OK, summary="Get available balance")
def get_employee_balance(
    employee_id: int = Path(..., gt=0), 
    category_id: int = Query(..., alias="categoryId"), 
    db: Session = Depends(get_db)
):
    return expense_controller.get_balance(db, employee_id, category_id)

@router.delete("/{expense_id}", status_code=status.HTTP_200_OK, summary="Delete an expense")
def delete_expense(
    expense_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
):
    return expense_controller.delete_expense(db, expense_id)