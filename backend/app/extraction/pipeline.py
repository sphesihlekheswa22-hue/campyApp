import os

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
from app.models import AnnualReport, ExtractedFinancial, GovernanceNarrative, ReportStatus

settings = get_settings()


def resolve_report_file_path(stored_path: str) -> str:
    normalized = stored_path.replace("\\", "/")
    if normalized.startswith("uploads/"):
        normalized = normalized[len("uploads/"):]
    return os.path.join(settings.upload_dir, normalized)


def run_extraction(report_id: int, report_year: str | None = None) -> None:
    db = SessionLocal()
    try:
        report = db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
        if not report:
            return

        report.status = ReportStatus.processing
        db.commit()

        file_path = resolve_report_file_path(report.file_path)
        if not os.path.exists(file_path):
            print(f"[EXTRACTION] File not found: {file_path}")
            report.status = ReportStatus.failed
            db.commit()
            return

        db.query(ExtractedFinancial).filter(ExtractedFinancial.report_id == report_id).delete()
        db.query(GovernanceNarrative).filter(GovernanceNarrative.report_id == report_id).delete()

        text = extract_text_from_pdf(file_path)
        tables = extract_tables_from_pdf(file_path)
        financial_year = report_year or detect_financial_year(text)

        financials = extract_financials_from_text(text, financial_year)
        financials += extract_financials_from_tables(tables, financial_year)

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

        governance_count = 0
        for gov in extract_governance_narratives(text):
            db.add(GovernanceNarrative(
                report_id=report_id,
                category=gov["category"],
                content=gov["content"],
                confidence_score=gov["confidence_score"],
            ))
            governance_count += 1

        if financial_count == 0 and governance_count == 0:
            print(f"[EXTRACTION] No data extracted for report {report_id}")
            report.status = ReportStatus.failed
        else:
            report.status = ReportStatus.complete
            print(f"[EXTRACTION] Report {report_id}: {financial_count} financials, {governance_count} governance items")
        db.commit()

        if report.status == ReportStatus.complete:
            from app.analytics.engine import run_company_analytics
            run_company_analytics(report.company_id, user_id=None)

    except Exception as e:
        print(f"[EXTRACTION ERROR] report {report_id}: {e}")
        report = db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
        if report:
            report.status = ReportStatus.failed
            db.commit()
    finally:
        db.close()


def recover_pending_extractions() -> None:
    """Re-queue reports stuck in pending/processing (e.g. after Render restart)."""
    db = SessionLocal()
    try:
        stuck = db.query(AnnualReport).filter(
            AnnualReport.status.in_([ReportStatus.pending, ReportStatus.processing])
        ).all()
        for report in stuck:
            path = resolve_report_file_path(report.file_path)
            if os.path.exists(path):
                print(f"[EXTRACTION] Recovering report {report.id}")
                run_extraction(report.id)
    finally:
        db.close()
