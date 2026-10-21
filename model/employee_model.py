from sqlalchemy import Column, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from database.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    department = Column(String(100), nullable=False)
    max_budget = Column(Numeric(10, 2), nullable=False, default=0.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ORM Relationships
    benefits = relationship("Benefit", back_populates="employee", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="employee", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        # Ignore legacy 'position' if passed from older tests or payloads
        kwargs.pop("position", None)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Employee(id={self.id}, name='{self.first_name} {self.last_name}', email='{self.email}', max_budget={self.max_budget})>"
