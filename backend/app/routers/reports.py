import os
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.security import get_current_user, require_roles
from app.config import get_settings
from app.database.session import get_db
from app.extraction.pipeline import resolve_report_file_path, run_extraction
from app.models import AnnualReport, ReportStatus, User, UserRole
from app.schemas import ReportResponse
from app.services.audit_service import log_audit

router = APIRouter(prefix="/reports", tags=["reports"])
settings = get_settings()


def _can_access_company(user: User, company_id: int) -> bool:
    if user.role == UserRole.platform_owner:
        return True
    return user.company_id == company_id


@router.get("/", response_model=list[ReportResponse])
def list_reports(
    company_id: Optional[int] = Query(None),
    status: Optional[ReportStatus] = Query(None),
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
    return query.order_by(AnnualReport.upload_date.desc()).all()


@router.post("/upload", response_model=ReportResponse)
async def upload_report(
    background_tasks: BackgroundTasks,
    request: Request,
    company_id: int = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner, UserRole.company_admin])),
):
    if not _can_access_company(current_user, company_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    os.makedirs(os.path.join(settings.upload_dir, "reports"), exist_ok=True)
    filename = f"{uuid.uuid4()}.pdf"
    rel_path = f"reports/{filename}"
    full_path = os.path.join(settings.upload_dir, rel_path)
    content = await file.read()
    with open(full_path, "wb") as f:
        f.write(content)

    report = AnnualReport(
        company_id=company_id,
        file_path=rel_path,
        status=ReportStatus.pending,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    log_audit(db, current_user.id, "upload_report", f"report:{report.id}", request.client.host if request.client else None)
    background_tasks.add_task(run_extraction, report.id)
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
    full_path = resolve_report_file_path(report.file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full_path, media_type="application/pdf", filename=f"report_{report_id}.pdf")
