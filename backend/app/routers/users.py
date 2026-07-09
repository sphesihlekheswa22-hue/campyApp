import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.auth.security import get_current_user, hash_password, require_roles
from app.config import get_settings
from app.database.session import get_db
from app.models import User, UserRole
from app.schemas import PaginatedResponse, UserCreateRequest, UserResponse, UserUpdateRequest
from app.services.audit_service import log_audit
from app.services.email_service import send_invite_email
from app.utils.pagination import paginate

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_me(
    data: UserUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    log_audit(db, current_user.id, "update_profile", f"user:{current_user.id}", request.client.host if request.client else None)
    return current_user


@router.post("/me/photo")
async def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    os.makedirs(os.path.join(settings.upload_dir, "photos"), exist_ok=True)
    ext = os.path.splitext(file.filename or "photo.jpg")[1]
    filename = f"{uuid.uuid4()}{ext}"
    path = os.path.join(settings.upload_dir, "photos", filename)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    current_user.profile_photo = f"/uploads/photos/{filename}"
    db.commit()
    log_audit(db, current_user.id, "upload_photo", f"user:{current_user.id}", request.client.host if request.client else None)
    return {"profile_photo": current_user.profile_photo}


@router.get("/", response_model=PaginatedResponse[UserResponse])
def list_users(
    search: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    company_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(User)
    if current_user.role == UserRole.company_admin:
        query = query.filter(User.company_id == current_user.company_id)
    elif current_user.role == UserRole.employee:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            (User.name.ilike(term))
            | (User.surname.ilike(term))
            | (User.email.ilike(term))
        )
    if role:
        query = query.filter(User.role == role)
    if company_id and current_user.role == UserRole.platform_owner:
        query = query.filter(User.company_id == company_id)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    query = query.order_by(User.created_at.desc())
    items, total, limit, offset = paginate(query, limit, offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/", response_model=UserResponse)
def create_user(
    data: UserCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner, UserRole.company_admin])),
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    if data.role == UserRole.platform_owner:
        raise HTTPException(status_code=403, detail="Cannot create platform owner accounts")
    if current_user.role == UserRole.company_admin:
        data.company_id = current_user.company_id
        if data.role != UserRole.employee:
            raise HTTPException(status_code=403, detail="Company admins can only add employees")
    temp_password = data.password or secrets.token_urlsafe(10)
    user = User(
        email=data.email,
        password_hash=hash_password(temp_password),
        name=data.name,
        surname=data.surname,
        role=data.role,
        company_id=data.company_id,
        phone_number=data.phone_number,
        is_active=True,
        must_change_password=True,
        invited_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    if data.send_invite_email:
        send_invite_email(data.email, temp_password, data.name)
    log_audit(db, current_user.id, "create_user", f"user:{user.id}", request.client.host if request.client else None)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role == UserRole.employee and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if current_user.role == UserRole.company_admin and user.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner, UserRole.company_admin])),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role == UserRole.company_admin and user.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    log_audit(db, current_user.id, "update_user", f"user:{user_id}", request.client.host if request.client else None)
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner, UserRole.company_admin])),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role == UserRole.company_admin and user.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    db.delete(user)
    db.commit()
    log_audit(db, current_user.id, "delete_user", f"user:{user_id}", request.client.host if request.client else None)
    return {"message": "User deleted"}
