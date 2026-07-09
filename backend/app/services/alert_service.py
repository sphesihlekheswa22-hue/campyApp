from datetime import datetime, timezone

from app.config import get_settings
from app.database.session import SessionLocal
from app.models import AnnualReport, NotificationType, ReportStatus, User, UserRole
from app.services.email_service import send_email
from app.services.notification_service import notify_platform_owners

settings = get_settings()


def run_health_alerts() -> dict:
    db = SessionLocal()
    try:
        pending = db.query(AnnualReport).filter(
            AnnualReport.status.in_([ReportStatus.pending, ReportStatus.processing])
        ).count()
        failed = db.query(AnnualReport).filter(AnnualReport.status == ReportStatus.failed).count()

        alerts = []
        if failed >= settings.alert_failed_extractions_threshold:
            alerts.append(f"{failed} failed extractions (threshold: {settings.alert_failed_extractions_threshold})")
        if pending >= settings.alert_pending_extractions_threshold:
            alerts.append(f"{pending} pending extractions (threshold: {settings.alert_pending_extractions_threshold})")

        if not alerts:
            return {"alerts_sent": 0}

        message = "System health alert:\n" + "\n".join(f"• {a}" for a in alerts)
        notify_platform_owners(
            db,
            NotificationType.system_alert,
            "Platform health alert",
            message,
            entity_ref="system:health",
        )

        alert_email = settings.alert_email or settings.platform_owner_email
        owner = db.query(User).filter(User.email == alert_email, User.role == UserRole.platform_owner).first()
        if owner:
            try:
                send_email(alert_email, "JSE Analytics — System Health Alert", message)
            except Exception as e:
                print(f"[ALERT EMAIL ERROR] {e}")

        return {"alerts_sent": len(alerts), "details": alerts}
    finally:
        db.close()
