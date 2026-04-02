from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import RoleRequired, get_current_user, get_db
from app.models.user import User, UserRole
from app.schemas.user import UserResponse, UserRoleUpdate
from app.services import user as user_service

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(user: User = Depends(get_current_user)):
    return user


@router.get("/", response_model=list[UserResponse])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(RoleRequired(UserRole.admin)),
):
    users, _ = user_service.get_users(db, skip, limit)
    return users


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleRequired(UserRole.admin)),
):
    target = user_service.get_user_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )
    return user_service.update_user_role(db, target, data.role)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleRequired(UserRole.admin)),
):
    target = user_service.get_user_by_id(db, user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )
    user_service.delete_user(db, target)
