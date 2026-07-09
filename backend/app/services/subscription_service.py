from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Company, SubscriptionStatus, User, UserRole

ALLOWED_STATUSES = {SubscriptionStatus.active, SubscriptionStatus.trial}


def assert_company_active(company: Company | None) -> None:
    """Raise if the company cannot use platform features (upload, etc.)."""
    if not company:
        raise HTTPException(status_code=403, detail="No company assigned to your account")
    if company.subscription_status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=403,
            detail=f"Company subscription is {company.subscription_status.value}. Contact your platform administrator.",
        )


def assert_user_company_active(db: Session, user: User) -> None:
    """Block company admins/employees when their company is inactive or suspended."""
    if user.role == UserRole.platform_owner:
        return
    if not user.company_id:
        raise HTTPException(status_code=403, detail="No company assigned to your account")
    company = db.query(Company).filter(Company.id == user.company_id).first()
    assert_company_active(company)
