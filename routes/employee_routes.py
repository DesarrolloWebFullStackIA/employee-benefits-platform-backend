from typing import List

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from controller import benefit_controller, employee_controller
from database.database import get_db
from schema.benefit_schema import BenefitCreate, BenefitResponse, BenefitUpdate
from schema.employee_schema import (
    EmployeeBudgetUpdate,
    EmployeeCreate,
    EmployeeDetailResponse,
    EmployeeResponse,
    EmployeeUpdate,
)

router = APIRouter(prefix="/employees", tags=["Employees"])
benefit_router = APIRouter(prefix="/benefits", tags=["Benefits"])


# ---------------------------------------------------------------------------
# Employee CRUD Endpoints (CA-BE-04.1)
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=List[EmployeeResponse],
    status_code=status.HTTP_200_OK,
    summary="List all employees with budget metrics",
)
@router.get(
    "/",
    response_model=List[EmployeeResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_all_employees(db: Session = Depends(get_db)):
    """Retrieve full employee catalog with aggregated budget cap, total allocated, and total spent."""
    return employee_controller.get_all_employees(db)


@router.get(
    "/{employee_id}",
    response_model=EmployeeDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get employee details by ID",
)
def get_employee_by_id(
    employee_id: int = Path(..., description="The ID of the employee to retrieve", gt=0),
    db: Session = Depends(get_db),
):
    """Retrieve an employee's detailed profile with category benefits and expenses breakdown."""
    return employee_controller.get_employee_by_id(db, employee_id)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new employee",
)
@router.post(
    "/",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_employee(
    employee_in: EmployeeCreate,
    db: Session = Depends(get_db),
):
    """Create a new employee validating unique email constraint and budget cap."""
    return employee_controller.create_employee(db, employee_in)


@router.put(
    "/{employee_id}",
    response_model=EmployeeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update employee personal information",
)
def update_employee(
    employee_in: EmployeeUpdate,
    employee_id: int = Path(..., description="The ID of the employee to update", gt=0),
    db: Session = Depends(get_db),
):
    """Update employee personal information verifying email collision."""
    return employee_controller.update_employee(db, employee_id, employee_in)


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an employee",
)
def delete_employee(
    employee_id: int = Path(..., description="The ID of the employee to delete", gt=0),
    db: Session = Depends(get_db),
):
    """Delete employee record with cascading removal of benefits and historical expenses."""
    employee_controller.delete_employee(db, employee_id)
    return None


# ---------------------------------------------------------------------------
# 1-Click Editable Budget Endpoint (CA-BE-04.2)
# ---------------------------------------------------------------------------


@router.patch(
    "/{employee_id}/budget",
    response_model=EmployeeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update total assigned budget in 1-click",
)
def update_employee_budget(
    budget_in: EmployeeBudgetUpdate,
    employee_id: int = Path(..., description="The ID of the employee to update budget", gt=0),
    db: Session = Depends(get_db),
):
    """Modify the employee's global budget cap.

    Enforces the business rule: new budget cannot be lower than committed spending
    (PENDING and APPROVED expenses). Returns HTTP 422 if violated.
    """
    return employee_controller.update_employee_budget(
        db, employee_id, budget_in.max_budget
    )


# ---------------------------------------------------------------------------
# Benefit Allocation Endpoints (CA-BE-04.3)
# ---------------------------------------------------------------------------


@router.get(
    "/{employee_id}/benefits",
    response_model=List[BenefitResponse],
    status_code=status.HTTP_200_OK,
    summary="List all category benefits for an employee",
)
def get_employee_benefits(
    employee_id: int = Path(..., description="The ID of the employee", gt=0),
    db: Session = Depends(get_db),
):
    """Retrieve all category benefit cup allocations for the specified employee."""
    return benefit_controller.get_benefits_by_employee(db, employee_id)


@router.post(
    "/{employee_id}/benefits",
    response_model=BenefitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a category benefit to an employee",
)
def assign_benefit(
    benefit_in: BenefitCreate,
    employee_id: int = Path(..., description="The ID of the employee", gt=0),
    db: Session = Depends(get_db),
):
    """Assign a category benefit cup validating category uniqueness and global cap."""
    return benefit_controller.assign_benefit_to_employee(db, employee_id, benefit_in)


@benefit_router.put(
    "/{benefit_id}",
    response_model=BenefitResponse,
    status_code=status.HTTP_200_OK,
    summary="Update category benefit allocation",
)
def update_benefit(
    benefit_in: BenefitUpdate,
    benefit_id: int = Path(..., description="The ID of the benefit to update", gt=0),
    db: Session = Depends(get_db),
):
    """Update the allocated amount of an existing category benefit."""
    return benefit_controller.update_benefit_allocation(db, benefit_id, benefit_in)


@benefit_router.delete(
    "/{benefit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an unused category benefit",
)
def delete_benefit(
    benefit_id: int = Path(..., description="The ID of the benefit to delete", gt=0),
    db: Session = Depends(get_db),
):
    """Delete a category benefit assignment if no expenses have been consumed against it."""
    benefit_controller.delete_benefit(db, benefit_id)
    return None
