import math
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import RoleRequired, get_db
from app.models.record import RecordType
from app.models.user import User, UserRole
from app.schemas.record import (
    MonthlyTotal,
    PaginatedRecords,
    RecordCreate,
    RecordResponse,
    RecordUpdate,
    SummaryResponse,
)
from app.services import record as record_service

router = APIRouter()


# --- Analytics endpoints (defined BEFORE {id} to avoid path conflicts) ---


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    db: Session = Depends(get_db),
    user: User = Depends(RoleRequired(UserRole.viewer)),
):
    return record_service.get_summary(db, user.id)


@router.get("/monthly", response_model=list[MonthlyTotal])
def get_monthly_totals(
    db: Session = Depends(get_db),
    user: User = Depends(RoleRequired(UserRole.analyst)),
):
    return record_service.get_monthly_totals(db, user.id)


@router.get("/recent", response_model=list[RecordResponse])
def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(RoleRequired(UserRole.viewer)),
):
    return record_service.get_recent_activity(db, user.id, limit)


@router.get("/export")
def export_records(
    format: str = Query("json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    user: User = Depends(RoleRequired(UserRole.analyst)),
):
    data = record_service.export_records(db, user.id, format)

    if format == "csv":
        return StreamingResponse(
            iter([data]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=records.csv"},
        )
    return data


# --- CRUD endpoints ---


@router.post("/", response_model=RecordResponse, status_code=status.HTTP_201_CREATED)
def create_record(
    data: RecordCreate,
    db: Session = Depends(get_db),
    user: User = Depends(RoleRequired(UserRole.admin)),
):
    return record_service.create_record(db, data, user.id)


@router.get("/", response_model=PaginatedRecords)
def list_records(
    type: Optional[RecordType] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(RoleRequired(UserRole.viewer)),
):
    has_filters = any([type, category, start_date, end_date])
    if has_filters and user.role == UserRole.viewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Filters require analyst role or higher",
        )

    skip = (page - 1) * per_page
    records, total = record_service.get_records(
        db, user.id, type, category, start_date, end_date, skip, per_page
    )
    return PaginatedRecords(
        items=records,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/{record_id}", response_model=RecordResponse)
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(RoleRequired(UserRole.viewer)),
):
    record = record_service.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    if record.user_id != user.id and user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return record


@router.put("/{record_id}", response_model=RecordResponse)
def update_record(
    record_id: int,
    data: RecordUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(RoleRequired(UserRole.admin)),
):
    record = record_service.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return record_service.update_record(db, record, data)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(RoleRequired(UserRole.admin)),
):
    record = record_service.get_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    record_service.delete_record(db, record)
