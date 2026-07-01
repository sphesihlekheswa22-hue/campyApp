from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database.session import get_db
from app.models import AnnualReport, GovernanceNarrative, User, UserRole
from app.schemas import GovernanceResponse

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/", response_model=list[GovernanceResponse])
def list_governance(
    company_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    report_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(GovernanceNarrative).join(AnnualReport)
    if current_user.role != UserRole.platform_owner:
        query = query.filter(AnnualReport.company_id == current_user.company_id)
    elif company_id:
        query = query.filter(AnnualReport.company_id == company_id)
    if report_id:
        query = query.filter(GovernanceNarrative.report_id == report_id)
    if category:
        query = query.filter(GovernanceNarrative.category == category)
    return query.order_by(GovernanceNarrative.id.desc()).all()


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(GovernanceNarrative.category).join(AnnualReport).distinct()
    if current_user.role != UserRole.platform_owner:
        query = query.filter(AnnualReport.company_id == current_user.company_id)
    return [c[0] for c in query.all()]
