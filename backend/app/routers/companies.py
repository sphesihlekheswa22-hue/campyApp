import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth.security import get_current_user, hash_password, require_roles
from app.config import get_settings
from app.database.session import get_db
from app.models import AnnualReport, Company, SubscriptionStatus, User, UserRole
from app.schemas import CompanyCreateRequest, CompanyListResponse, CompanyResponse, CompanyUpdateRequest, PaginatedResponse
from app.utils.pagination import paginate
from app.services.audit_service import log_audit
from app.services.email_service import send_invite_email

router = APIRouter(prefix="/companies", tags=["companies"])
settings = get_settings()


@router.get("/", response_model=PaginatedResponse[CompanyListResponse])
def list_companies(
    search: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    subscription_status: Optional[SubscriptionStatus] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Company)
    if current_user.role == UserRole.company_admin or current_user.role == UserRole.employee:
        if not current_user.company_id:
            return []
        query = query.filter(Company.id == current_user.company_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Company.company_name.ilike(term),
                Company.registration_number.ilike(term),
                Company.industry.ilike(term),
            )
        )
    if industry:
        query = query.filter(Company.industry == industry)
    if subscription_status:
        query = query.filter(Company.subscription_status == subscription_status)

    query = query.order_by(Company.company_name)
    companies, total, limit, offset = paginate(query, limit, offset)
    if not companies:
        return PaginatedResponse(items=[], total=total, limit=limit, offset=offset)

    counts = dict(
        db.query(AnnualReport.company_id, func.count(AnnualReport.id))
        .filter(AnnualReport.company_id.in_([c.id for c in companies]))
        .group_by(AnnualReport.company_id)
        .all()
    )

    items = [
        CompanyListResponse(
            id=c.id,
            company_name=c.company_name,
            registration_number=c.registration_number,
            website=c.website,
            logo=c.logo,
            industry=c.industry,
            jse_code=c.jse_code,
            sector=c.sector,
            listing_date=c.listing_date,
            market_cap=c.market_cap,
            subscription_status=c.subscription_status,
            created_at=c.created_at,
            report_count=counts.get(c.id, 0),
        )
        for c in companies
    ]
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/", response_model=CompanyResponse)
def create_company(
    data: CompanyCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner])),
):
    if db.query(Company).filter(Company.registration_number == data.registration_number).first():
        raise HTTPException(status_code=400, detail="Registration number already exists")
    if data.admin_email and db.query(User).filter(User.email == data.admin_email).first():
        raise HTTPException(status_code=400, detail="Admin email already exists")

    company_data = data.model_dump(exclude={"admin_email", "admin_password", "admin_name", "admin_surname"})
    company = Company(**company_data)
    db.add(company)
    db.flush()

    if data.admin_email:
        admin = User(
            email=data.admin_email,
            password_hash=hash_password(data.admin_password),
            name=data.admin_name,
            surname=data.admin_surname,
            role=UserRole.company_admin,
            company_id=company.id,
            is_active=True,
            must_change_password=True,
            invited_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.flush()
        send_invite_email(data.admin_email, data.admin_password, data.admin_name)

    db.commit()
    db.refresh(company)
    log_audit(db, current_user.id, "create_company", f"company:{company.id}", request.client.host if request.client else None)
    return company


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if current_user.role != UserRole.platform_owner and current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return company


@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: int,
    data: CompanyUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner, UserRole.company_admin])),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if current_user.role == UserRole.company_admin and current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    for field, value in data.model_dump(exclude_unset=True).items():
        if current_user.role == UserRole.company_admin and field == "subscription_status":
            continue
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    log_audit(db, current_user.id, "update_company", f"company:{company_id}", request.client.host if request.client else None)
    return company


@router.post("/{company_id}/logo")
async def upload_logo(
    company_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner, UserRole.company_admin])),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if current_user.role == UserRole.company_admin and current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    os.makedirs(os.path.join(settings.upload_dir, "logos"), exist_ok=True)
    ext = os.path.splitext(file.filename or "logo.png")[1]
    filename = f"{uuid.uuid4()}{ext}"
    path = os.path.join(settings.upload_dir, "logos", filename)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    company.logo = f"/uploads/logos/{filename}"
    db.commit()
    log_audit(db, current_user.id, "upload_logo", f"company:{company_id}", request.client.host if request.client else None)
    return {"logo": company.logo}


@router.delete("/{company_id}")
def delete_company(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner])),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()
    log_audit(db, current_user.id, "delete_company", f"company:{company_id}", request.client.host if request.client else None)
    return {"message": "Company deleted"}
