import os
import tempfile

from app.config import get_settings
from app.database.session import SessionLocal
from app.extraction.extractors import (
    detect_financial_year,
    extract_financials_from_tables,
    extract_financials_from_text,
    extract_governance_narratives,
    extract_tables_from_pdf,
    extract_text_from_pdf,
)
from app.extraction.llm_extractor import extract_financials_with_llm, extract_governance_with_llm
from app.models import AnnualReport, ExtractedFinancial, GovernanceNarrative, NotificationType, ReportStatus, UserRole
from app.services.notification_service import notify_company_users
from app.services.storage_service import storage

settings = get_settings()


def resolve_report_file_path(stored_path: str) -> str:
    return storage.resolve_local_path(stored_path)


def run_extraction(report_id: int, report_year: str | None = None) -> tuple[bool, str | None]:
    db = SessionLocal()
    temp_path: str | None = None
    try:
        report = db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
        if not report:
            return False, "Report not found"

        report.status = ReportStatus.processing
        db.commit()

        if not storage.exists(report.file_path):
            print(f"[EXTRACTION] File not found: {report.file_path}")
            report.status = ReportStatus.failed
            db.commit()
            msg = "PDF file not found in storage. Re-upload the report (use S3/R2 on production)."
            _notify_extraction_result(db, report, success=False, error=msg)
            return False, msg

        file_path = resolve_report_file_path(report.file_path)
        if file_path and tempfile.gettempdir() in file_path:
            temp_path = file_path

        db.query(ExtractedFinancial).filter(ExtractedFinancial.report_id == report_id).delete()
        db.query(GovernanceNarrative).filter(GovernanceNarrative.report_id == report_id).delete()

        text = extract_text_from_pdf(file_path)
        text_len = len(text.strip())
        if text_len < 50:
            print(f"[EXTRACTION] Very little text ({text_len} chars) for report {report_id}")
            report.status = ReportStatus.failed
            db.commit()
            msg = "PDF has little or no readable text. Upload a text-based PDF or enable OCR (OCR_ENABLED=true)."
            _notify_extraction_result(db, report, success=False, error=msg)
            return False, msg

        tables = extract_tables_from_pdf(file_path)
        financial_year = report_year or detect_financial_year(text)

        financials = extract_financials_from_text(text, financial_year)
        financials += extract_financials_from_tables(tables, financial_year)

        if not financials:
            financials = extract_financials_with_llm(text, financial_year)

        seen = set()
        financial_count = 0
        for fin in financials:
            key = (fin["metric_name"], fin["financial_year"])
            if key in seen:
                continue
            seen.add(key)
            db.add(ExtractedFinancial(
                report_id=report_id,
                financial_year=fin["financial_year"],
                metric_name=fin["metric_name"],
                metric_value=fin["metric_value"],
                category=fin["category"],
            ))
            financial_count += 1

        governance_items = extract_governance_narratives(text)
        llm_items = extract_governance_with_llm(text)
        gov_seen = {g["category"] for g in governance_items}
        for item in llm_items:
            if item["category"] not in gov_seen:
                governance_items.append(item)
                gov_seen.add(item["category"])

        governance_count = 0
        for gov in governance_items:
            db.add(GovernanceNarrative(
                report_id=report_id,
                category=gov["category"],
                content=gov["content"],
                confidence_score=gov["confidence_score"],
            ))
            governance_count += 1

        if financial_count == 0 and governance_count == 0:
            print(f"[EXTRACTION] No data extracted for report {report_id} ({text_len} chars of text)")
            report.status = ReportStatus.failed
            msg = "Could not match financial or governance patterns in this PDF. Try Retry or set OPENAI_API_KEY for AI-assisted extraction."
            db.commit()
            _notify_extraction_result(db, report, success=False, error=msg)
            return False, msg

        report.status = ReportStatus.complete
        print(f"[EXTRACTION] Report {report_id}: {financial_count} financials, {governance_count} governance items")
        db.commit()

        from app.analytics.engine import run_company_analytics
        run_company_analytics(report.company_id, user_id=None)
        _notify_extraction_result(db, report, success=True)
        return True, None

    except Exception as e:
        print(f"[EXTRACTION ERROR] report {report_id}: {e}")
        report = db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
        if report:
            report.status = ReportStatus.failed
            db.commit()
            _notify_extraction_result(db, report, success=False, error=str(e))
        return False, str(e)
    finally:
        if temp_path and os.path.isfile(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        db.close()


def _notify_extraction_result(db, report, success: bool, error: str | None = None) -> None:
    if success:
        notify_company_users(
            db,
            report.company_id,
            NotificationType.extraction_complete,
            "Report extraction complete",
            f"Report #{report.id} was extracted successfully. Analytics have been updated.",
            entity_ref=f"report:{report.id}",
            roles=[UserRole.company_admin, UserRole.employee],
        )
    else:
        notify_company_users(
            db,
            report.company_id,
            NotificationType.extraction_failed,
            "Report extraction failed",
            error or f"Report #{report.id} could not be extracted. Try re-uploading or use Retry.",
            entity_ref=f"report:{report.id}",
            roles=[UserRole.company_admin],
        )


def recover_pending_extractions() -> None:
    """Enqueue stuck reports via job queue."""
    from app.services.job_service import enqueue_job
    db = SessionLocal()
    try:
        stuck = db.query(AnnualReport).filter(
            AnnualReport.status.in_([ReportStatus.pending, ReportStatus.processing])
        ).all()
        for report in stuck:
            if storage.exists(report.file_path):
                print(f"[EXTRACTION] Re-queuing report {report.id}")
                enqueue_job(db, "extraction", {"report_id": report.id})
    finally:
        db.close()
