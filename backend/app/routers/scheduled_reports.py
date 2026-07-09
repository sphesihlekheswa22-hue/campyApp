from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import get_current_user, require_roles
from app.database.session import get_db
from app.models import ScheduledReport, User, UserRole
from app.schemas import ScheduledReportCreateRequest, ScheduledReportResponse

router = APIRouter(prefix="/scheduled-reports", tags=["scheduled-reports"])


def _can_access(user: User, company_id: int) -> bool:
    if user.role == UserRole.platform_owner:
        return True
    return user.company_id == company_id


@router.get("/", response_model=list[ScheduledReportResponse])
def list_schedules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ScheduledReport)
    if current_user.role != UserRole.platform_owner:
        query = query.filter(ScheduledReport.user_id == current_user.id)
    return query.order_by(ScheduledReport.created_at.desc()).all()


@router.post("/", response_model=ScheduledReportResponse)
def create_schedule(
    data: ScheduledReportCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner, UserRole.company_admin])),
):
    if not _can_access(current_user, data.company_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    schedule = ScheduledReport(
        company_id=data.company_id,
        user_id=current_user.id,
        report_type=data.report_type,
        frequency=data.frequency,
        is_active=True,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner, UserRole.company_admin])),
):
    schedule = db.query(ScheduledReport).filter(ScheduledReport.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if current_user.role != UserRole.platform_owner and schedule.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    db.delete(schedule)
    db.commit()
    return {"message": "Schedule deleted"}
