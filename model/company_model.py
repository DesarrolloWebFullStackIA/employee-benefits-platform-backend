from sqlalchemy import Column, Numeric, Integer,func
from database.database import Base


class Company(Base):
    __tablename__ = "company"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    global_budget =  Column(Numeric(10, 2), nullable=False, default=0.00)

    def __repr__(self) -> str:
        return (
            f"Company(id={self.id!r}, "
            f"global_budget={self.global_budget!r})"
        )

