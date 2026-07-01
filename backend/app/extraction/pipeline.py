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


def run_extraction(report_id: int) -> None:
    db = SessionLocal()
    try:
        report = db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
        if not report:
            return

        report.status = ReportStatus.processing
        db.commit()

        file_path = os.path.join(settings.upload_dir, report.file_path)
        if not os.path.exists(file_path):
            report.status = ReportStatus.failed
            db.commit()
            return

        db.query(ExtractedFinancial).filter(ExtractedFinancial.report_id == report_id).delete()
        db.query(GovernanceNarrative).filter(GovernanceNarrative.report_id == report_id).delete()

        text = extract_text_from_pdf(file_path)
        tables = extract_tables_from_pdf(file_path)
        financial_year = detect_financial_year(text)

        financials = extract_financials_from_text(text, financial_year)
        financials += extract_financials_from_tables(tables, financial_year)

        seen = set()
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

        for gov in extract_governance_narratives(text):
            db.add(GovernanceNarrative(
                report_id=report_id,
                category=gov["category"],
                content=gov["content"],
                confidence_score=gov["confidence_score"],
            ))

        report.status = ReportStatus.complete
        db.commit()

        from app.analytics.engine import run_company_analytics
        run_company_analytics(report.company_id)

    except Exception as e:
        print(f"[EXTRACTION ERROR] report {report_id}: {e}")
        report = db.query(AnnualReport).filter(AnnualReport.id == report_id).first()
        if report:
            report.status = ReportStatus.failed
            db.commit()
    finally:
        db.close()
