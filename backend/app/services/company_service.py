from sqlalchemy.orm import Session

from app.models import (
    AnalyticsResult,
    AnnualReport,
    AuditLog,
    Company,
    EmailVerification,
    ExtractedFinancial,
    GovernanceNarrative,
    Notification,
    PasswordResetToken,
    ScheduledReport,
    User,
)
from app.services.storage_service import storage


def delete_company_cascade(db: Session, company: Company) -> None:
    """Remove a company and all related data safely."""
    company_id = company.id
    user_ids = [row[0] for row in db.query(User.id).filter(User.company_id == company_id).all()]

    if user_ids:
        db.query(AuditLog).filter(AuditLog.user_id.in_(user_ids)).update(
            {AuditLog.user_id: None}, synchronize_session=False
        )
        db.query(Notification).filter(Notification.user_id.in_(user_ids)).delete(synchronize_session=False)
        db.query(PasswordResetToken).filter(PasswordResetToken.user_id.in_(user_ids)).delete(synchronize_session=False)
        db.query(EmailVerification).filter(EmailVerification.user_id.in_(user_ids)).delete(synchronize_session=False)
        db.query(ScheduledReport).filter(ScheduledReport.user_id.in_(user_ids)).delete(synchronize_session=False)

    db.query(Notification).filter(Notification.company_id == company_id).delete(synchronize_session=False)
    db.query(ScheduledReport).filter(ScheduledReport.company_id == company_id).delete(synchronize_session=False)
    db.query(AnalyticsResult).filter(AnalyticsResult.company_id == company_id).delete(synchronize_session=False)

    reports = db.query(AnnualReport).filter(AnnualReport.company_id == company_id).all()
    report_ids = [r.id for r in reports]
    if report_ids:
        db.query(ExtractedFinancial).filter(ExtractedFinancial.report_id.in_(report_ids)).delete(synchronize_session=False)
        db.query(GovernanceNarrative).filter(GovernanceNarrative.report_id.in_(report_ids)).delete(synchronize_session=False)

    for report in reports:
        if report.file_path and storage.exists(report.file_path):
            storage.delete(report.file_path)
    db.query(AnnualReport).filter(AnnualReport.company_id == company_id).delete(synchronize_session=False)

    if company.logo:
        key = _storage_key(company.logo)
        if key and storage.exists(key):
            storage.delete(key)

    db.query(User).filter(User.company_id == company_id).delete(synchronize_session=False)
    db.delete(company)


def _storage_key(path: str) -> str | None:
    if not path:
        return None
    if path.startswith("/api/files/"):
        return path[len("/api/files/"):]
    if path.startswith("/uploads/"):
        return path[len("/uploads/"):]
    return path.lstrip("/")
