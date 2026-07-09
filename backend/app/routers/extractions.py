from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import get_current_user, require_roles
from app.database.session import get_db
from app.extraction.pipeline import resolve_report_file_path, run_extraction
from app.extraction.extractors import extract_text_from_pdf
from app.models import AnnualReport, BackgroundJob, ExtractedFinancial, GovernanceNarrative, JobStatus, ReportStatus, User, UserRole
from app.schemas import FinancialResponse, GovernanceResponse, ReportExtractionSummary, ReportResponse
from app.services.job_service import enqueue_job
from app.services.storage_service import storage

router = APIRouter(prefix="/extractions", tags=["extractions"])


def _can_access_report(user: User, report: AnnualReport) -> bool:
    if user.role == UserRole.platform_owner:
        return True
    return user.company_id == report.company_id


@router.get("/report/{report_id}/summary", response_model=ReportExtractionSummary)
def get_extraction_summary(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _can_access_report(current_user, report):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    financials = db.query(ExtractedFinancial).filter(ExtractedFinancial.report_id == report_id).all()
    governance = db.query(GovernanceNarrative).filter(GovernanceNarrative.report_id == report_id).all()
    issues: list[str] = []

    if report.status == ReportStatus.failed:
        if not storage.exists(report.file_path):
            issues.append("PDF file not found in storage — re-upload the report (configure S3/R2 on Render)")
        else:
            last_job = (
                db.query(BackgroundJob)
                .filter(BackgroundJob.job_type == "extraction")
                .filter(BackgroundJob.payload_json.contains(f'"report_id": {report_id}'))
                .filter(BackgroundJob.error_message.isnot(None))
                .order_by(BackgroundJob.completed_at.desc())
                .first()
            )
            if last_job and last_job.error_message:
                issues.append(last_job.error_message)
            else:
                try:
                    path = resolve_report_file_path(report.file_path)
                    char_count = len(extract_text_from_pdf(path).strip())
                    if char_count < 50:
                        issues.append("PDF has little or no readable text — it may be scanned. Enable OCR_ENABLED or upload a text-based PDF")
                    else:
                        issues.append(
                            f"Extraction failed — {char_count:,} characters were read but no financial/governance patterns matched. Click Retry or set OPENAI_API_KEY for AI-assisted extraction"
                        )
                except Exception as exc:
                    issues.append(f"Could not read PDF: {exc}")
    elif report.status in (ReportStatus.pending, ReportStatus.processing):
        issues.append("Extraction is still in progress")
    if report.status == ReportStatus.complete and not financials:
        issues.append("No financial metrics were extracted — check table layout in the PDF")
    if report.status == ReportStatus.complete and not governance:
        issues.append("No governance narratives found — keywords may not match this report's wording")

    financial_year = financials[0].financial_year if financials else None

    return ReportExtractionSummary(
        report_id=report_id,
        status=report.status,
        financial_count=len(financials),
        governance_count=len(governance),
        financial_year=financial_year,
        extraction_issues=issues,
    )


@router.get("/report/{report_id}/financials", response_model=list[FinancialResponse])
def get_financials(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _can_access_report(current_user, report):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return db.query(ExtractedFinancial).filter(ExtractedFinancial.report_id == report_id).all()


@router.get("/report/{report_id}/governance", response_model=list[GovernanceResponse])
def get_governance_by_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if not _can_access_report(current_user, report):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return db.query(GovernanceNarrative).filter(GovernanceNarrative.report_id == report_id).all()


@router.post("/retry/{report_id}", response_model=ReportResponse)
def retry_extraction(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner, UserRole.company_admin])),
):
    report = db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role != UserRole.platform_owner and current_user.company_id != report.company_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    report.status = ReportStatus.pending
    db.commit()
    enqueue_job(db, "extraction", {"report_id": report_id})
    return report
