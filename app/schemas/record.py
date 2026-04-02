from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, Field

from app.models.record import RecordType


class RecordCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Must be a positive number")
    type: RecordType = Field(...)
    category: str = Field(..., min_length=1, max_length=50)
    date: date_type = Field(default_factory=date_type.today)
    notes: Optional[str] = Field(None, max_length=500)

    model_config = {"populate_by_name": True}


class RecordUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    type: Optional[RecordType] = Field(None)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    date: Optional[date_type] = Field(None)
    notes: Optional[str] = Field(None, max_length=500)


class RecordResponse(BaseModel):
    id: int
    amount: float
    type: RecordType
    category: str
    date: date_type
    notes: Optional[str]
    user_id: int

    model_config = {"from_attributes": True}


class PaginatedRecords(BaseModel):
    items: list[RecordResponse]
    total: int
    page: int
    per_page: int
    pages: int


class CategoryBreakdown(BaseModel):
    category: str
    type: RecordType
    total: float


class SummaryResponse(BaseModel):
    total_income: float
    total_expenses: float
    balance: float
    by_category: list[CategoryBreakdown]


class MonthlyTotal(BaseModel):
    month: str
    income: float
    expense: float
