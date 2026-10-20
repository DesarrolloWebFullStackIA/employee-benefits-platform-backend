from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session
from model.company_model import Company


def get_global_budget(db: Session) -> Decimal:
    """Returns the company's global budget."""
    company = db.query(Company).first()

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="No existe la configuración de la empresa.",
        )

    return company.global_budget


def update_global_budget(
    db: Session,
    global_budget: Decimal,
) -> Company:
    """Update the company's global budget."""
    if global_budget < 0:
        raise HTTPException(
            status_code=400,
            detail="El presupuesto global no puede ser negativo.",
        )

    company = db.query(Company).first()

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="No existe la configuración de la empresa.",
        )

    company.global_budget = global_budget

    try:
        db.commit()
        db.refresh(company)
    except Exception:
        db.rollback()
        raise

    return company


def create_company(
    db: Session,
    global_budget: Decimal,
) -> Company:
    """Create the company configuration if it does not yet exist."""
    if global_budget < 0:
        raise HTTPException(
            status_code=400,
            detail="El presupuesto global no puede ser negativo.",
        )

    company = db.query(Company).first()

    if company is not None:
        raise HTTPException(
            status_code=409,
            detail="La configuración de la empresa ya existe.",
        )

    company = Company(global_budget=global_budget)
    db.add(company)

    try:
        db.commit()
        db.refresh(company)
    except Exception:
        db.rollback()
        raise

    return company
