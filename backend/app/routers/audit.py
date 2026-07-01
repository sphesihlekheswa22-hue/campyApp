from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.security import require_roles
from app.database.session import get_db
from app.models import AuditLog, User, UserRole
from app.schemas import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/", response_model=list[AuditLogResponse])
def list_audit_logs(
    search: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner])),
):
    query = db.query(AuditLog, User.email).outerjoin(User, AuditLog.user_id == User.id)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                AuditLog.action.ilike(term),
                AuditLog.entity.ilike(term),
                User.email.ilike(term),
            )
        )
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action.strip()}%"))
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    results = query.order_by(AuditLog.timestamp.desc()).limit(500).all()
    return [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action,
            entity=log.entity,
            timestamp=log.timestamp,
            ip_address=log.ip_address,
            user_email=email,
        )
        for log, email in results
    ]
