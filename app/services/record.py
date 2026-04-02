import csv
import io
from datetime import date
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.record import FinancialRecord, RecordType
from app.schemas.record import RecordCreate, RecordResponse, RecordUpdate


def create_record(db: Session, data: RecordCreate, user_id: int) -> FinancialRecord:
    record = FinancialRecord(**data.model_dump(), user_id=user_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_records(
    db: Session,
    user_id: int,
    record_type: Optional[RecordType] = None,
    category: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[FinancialRecord], int]:
    query = db.query(FinancialRecord).filter(FinancialRecord.user_id == user_id)

    if record_type:
        query = query.filter(FinancialRecord.type == record_type)
    if category:
        query = query.filter(FinancialRecord.category == category)
    if start_date:
        query = query.filter(FinancialRecord.date >= start_date)
    if end_date:
        query = query.filter(FinancialRecord.date <= end_date)

    total = query.count()
    records = query.order_by(FinancialRecord.date.desc()).offset(skip).limit(limit).all()
    return records, total


def get_record_by_id(db: Session, record_id: int) -> Optional[FinancialRecord]:
    return db.query(FinancialRecord).filter(FinancialRecord.id == record_id).first()


def update_record(
    db: Session, record: FinancialRecord, data: RecordUpdate
) -> FinancialRecord:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, record: FinancialRecord) -> None:
    db.delete(record)
    db.commit()


def get_summary(db: Session, user_id: int) -> dict:
    type_totals = (
        db.query(FinancialRecord.type, func.sum(FinancialRecord.amount))
        .filter(FinancialRecord.user_id == user_id)
        .group_by(FinancialRecord.type)
        .all()
    )

    totals = {row[0].value: row[1] or 0 for row in type_totals}
    income = totals.get("income", 0)
    expenses = totals.get("expense", 0)

    category_breakdown = (
        db.query(
            FinancialRecord.category,
            FinancialRecord.type,
            func.sum(FinancialRecord.amount),
        )
        .filter(FinancialRecord.user_id == user_id)
        .group_by(FinancialRecord.category, FinancialRecord.type)
        .all()
    )

    return {
        "total_income": income,
        "total_expenses": expenses,
        "balance": income - expenses,
        "by_category": [
            {"category": row[0], "type": row[1].value, "total": row[2]}
            for row in category_breakdown
        ],
    }


def get_monthly_totals(db: Session, user_id: int) -> list[dict]:
    # SQLite strftime for year-month grouping
    month_col = func.strftime("%Y-%m", FinancialRecord.date)
    rows = (
        db.query(month_col, FinancialRecord.type, func.sum(FinancialRecord.amount))
        .filter(FinancialRecord.user_id == user_id)
        .group_by(month_col, FinancialRecord.type)
        .order_by(month_col)
        .all()
    )

    monthly: dict[str, dict] = {}
    for month, rec_type, total in rows:
        if month not in monthly:
            monthly[month] = {"month": month, "income": 0, "expense": 0}
        monthly[month][rec_type.value] = total or 0

    return list(monthly.values())


def get_recent_activity(
    db: Session, user_id: int, limit: int = 10
) -> list[FinancialRecord]:
    return (
        db.query(FinancialRecord)
        .filter(FinancialRecord.user_id == user_id)
        .order_by(FinancialRecord.date.desc(), FinancialRecord.id.desc())
        .limit(limit)
        .all()
    )


def export_records(
    db: Session, user_id: int, fmt: str = "json"
) -> str | list[dict]:
    records = (
        db.query(FinancialRecord)
        .filter(FinancialRecord.user_id == user_id)
        .order_by(FinancialRecord.date.desc())
        .all()
    )

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["id", "amount", "type", "category", "date", "notes"],
        )
        writer.writeheader()
        for r in records:
            writer.writerow(
                {
                    "id": r.id,
                    "amount": r.amount,
                    "type": r.type.value,
                    "category": r.category,
                    "date": r.date.isoformat(),
                    "notes": r.notes or "",
                }
            )
        return output.getvalue()

    return [
        RecordResponse.model_validate(r).model_dump(mode="json") for r in records
    ]
