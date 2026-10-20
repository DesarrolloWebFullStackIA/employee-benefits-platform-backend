from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, func, true
from sqlalchemy.orm import relationship

from database.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)
    icon = Column(String(100), nullable=False)
    color = Column(String(50), nullable=False)
    budget = Column(Numeric(10, 2), nullable=False, default=0.00)
    active = Column(Boolean, nullable=False, default=True, server_default=true())
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ORM Relationships
    benefits = relationship("Benefit", back_populates="category")
    expenses = relationship("Expense", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', budget={self.budget})>"
