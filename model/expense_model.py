from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from database.database import Base


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(
        Integer,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount = Column(Numeric(10, 2), nullable=False)
    concept = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    receipt_type = Column(String(10), nullable=True)
    receipt_url = Column(String(500), nullable=True)
    rejection_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

  
    employee = relationship("Employee", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")

    def __repr__(self) -> str:
        return (
            f"<Expense(id={self.id}, employee_id={self.employee_id}, "
            f"category_id={self.category_id}, amount={self.amount}, status='{self.status}')>"
        )