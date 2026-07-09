import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.security import get_current_user, require_roles
from app.config import get_settings
from app.database.session import get_db
from app.models import AnnualReport, NotificationType, ReportStatus, User, UserRole
from app.schemas import PaginatedResponse, ReportResponse
from app.services.audit_service import log_audit
from app.services.job_service import enqueue_job
from app.services.notification_service import notify_company_users
from app.services.storage_service import storage
from app.utils.pagination import paginate

router = APIRouter(prefix="/reports", tags=["reports"])
settings = get_settings()


def _can_access_company(user: User, company_id: int) -> bool:
    if user.role == UserRole.platform_owner:
        return True
    return user.company_id == company_id


@router.get("/", response_model=PaginatedResponse[ReportResponse])
def list_reports(
    company_id: Optional[int] = Query(None),
    status: Optional[ReportStatus] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(AnnualReport)
    if current_user.role != UserRole.platform_owner:
        query = query.filter(AnnualReport.company_id == current_user.company_id)
    elif company_id:
        query = query.filter(AnnualReport.company_id == company_id)
    if status:
        query = query.filter(AnnualReport.status == status)
    query = query.order_by(AnnualReport.upload_date.desc())
    items, total, limit, offset = paginate(query, limit, offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/upload", response_model=ReportResponse)
async def upload_report(
    request: Request,
    company_id: int = Query(...),
    report_year: Optional[str] = Query(None, description="Optional FY tag e.g. 2024"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.company_admin])),
):
    if not _can_access_company(current_user, company_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    filename = f"{uuid.uuid4()}.pdf"
    rel_path = f"reports/{filename}"
    content = await file.read()
    storage.save(rel_path, content)

    report = AnnualReport(
        company_id=company_id,
        file_path=rel_path,
        status=ReportStatus.pending,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    log_audit(db, current_user.id, "upload_report", f"report:{report.id}", request.client.host if request.client else None)

    year_tag = (report_year or "").strip() or None
    enqueue_job(db, "extraction", {"report_id": report.id, "report_year": year_tag})

    notify_company_users(
        db,
        company_id,
        NotificationType.report_uploaded,
        "New report uploaded",
        f"Report #{report.id} is queued for extraction.",
        entity_ref=f"report:{report.id}",
        roles=[UserRole.company_admin, UserRole.employee],
    )
    return report


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _can_access_company(current_user, report.company_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return report


@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _can_access_company(current_user, report.company_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if not storage.exists(report.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    data = storage.read(report.file_path)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_{report_id}.pdf"'},
    )
