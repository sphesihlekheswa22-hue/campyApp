from sqlalchemy.orm import Session

from app.models import AuditLog


def log_audit(
    db: Session,
    user_id: int | None,
    action: str,
    entity: str,
    ip_address: str | None = None,
) -> None:
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
