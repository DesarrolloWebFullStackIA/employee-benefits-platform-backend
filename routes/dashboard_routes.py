from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from controller import dashboard_controller
from database.database import get_db


from typing import List

from schema.dashboard_schema import (
    DashboardStatsSchema,
    CategoryStatsSchema,
    RecentEmployeeSchema
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStatsSchema)
def get_dashboard_stats(db: Session = Depends(get_db)):
    return dashboard_controller.get_dashboard_stats(db)

@router.get("/recent-employees",response_model=List[RecentEmployeeSchema],)
def get_recent_employees(db: Session = Depends(get_db)):
    return dashboard_controller.get_recent_employees(db)

@router.get("/categories", response_model=List[CategoryStatsSchema])
def get_category_stats(db: Session = Depends(get_db)):
    return dashboard_controller.get_category_stats(db)