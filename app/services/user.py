from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User, UserRole


def get_users(db: Session, skip: int = 0, limit: int = 20) -> tuple[list[User], int]:
    total = db.query(User).count()
    users = db.query(User).offset(skip).limit(limit).all()
    return users, total


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def update_user_role(db: Session, user: User, role: UserRole) -> User:
    user.role = role
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()
