
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from controller import company_controller
from schema.company_schema import CompanyBudgetSchema, CompanySchema


router = APIRouter(prefix="/company", tags=["Company"])


@router.get("/budget", response_model=CompanyBudgetSchema)
def get_global_budget(db: Session = Depends(get_db)):
    global_budget = company_controller.get_global_budget(db)

    return {"global_budget": global_budget}

@router.put("/budget", response_model=CompanySchema)
def update_global_budget(
    data: CompanyBudgetSchema,
    db: Session = Depends(get_db),
):
    return company_controller.update_global_budget(
        db=db,
        global_budget=data.global_budget,
    )
