from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models.user import User, UserRole
from app.routers import auth, records, users
from app.services.auth import hash_password


def seed_admin():
    """Create a default admin user if no users exist."""
    db: Session = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                username="admin",
                hashed_password=hash_password("admin123"),
                role=UserRole.admin,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_admin()
    yield


app = FastAPI(
    title="Finance Tracker API",
    description=(
        "A personal finance tracking system with role-based access control. "
        "Supports income/expense management, analytics, and CSV/JSON export."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(records.router, prefix="/records", tags=["Financial Records"])
app.include_router(users.router, prefix="/users", tags=["User Management"])


@app.get("/", tags=["Health"])
def root():
    return {"message": "Finance Tracker API is running", "docs": "/docs"}
