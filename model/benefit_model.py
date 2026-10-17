from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import relationship

from database.database import Base


class Benefit(Base):
    __tablename__ = "benefits"
    __table_args__ = (
        UniqueConstraint("employee_id", "category_id", name="uq_employee_category"),
    )

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
    allocated_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    spent_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ORM Relationships
    employee = relationship("Employee", back_populates="benefits")
    category = relationship("Category", back_populates="benefits")

    def __repr__(self) -> str:
        return (
            f"<Benefit(id={self.id}, employee_id={self.employee_id}, "
            f"category_id={self.category_id}, allocated={self.allocated_amount}, "
            f"spent={self.spent_amount})>"
        )
