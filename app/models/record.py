import enum
from datetime import date

from sqlalchemy import Column, Date, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class RecordType(str, enum.Enum):
    income = "income"
    expense = "expense"


class FinancialRecord(Base):
    __tablename__ = "financial_records"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    type = Column(Enum(RecordType), nullable=False)
    category = Column(String, nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    notes = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", backref="records")
