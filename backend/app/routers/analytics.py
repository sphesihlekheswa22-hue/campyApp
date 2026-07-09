import json
import os
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.analytics.engine import get_benchmarking, run_company_analytics
from app.auth.security import get_current_user, require_roles
from app.database.session import get_db
from app.models import AnalyticsResult, AnnualReport, Company, ExtractedFinancial, GovernanceNarrative, User, UserRole
from app.config import get_settings
from app.models import BackgroundJob, JobStatus
from app.schemas import AnalyticsResultResponse, SystemHealthResponse
from app.models import ReportStatus, User as UserModel

settings = get_settings()

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _can_access(user: User, company_id: int) -> bool:
    if user.role == UserRole.platform_owner:
        return True
    return user.company_id == company_id


@router.get("/company/{company_id}")
def get_company_analytics(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_access(current_user, company_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    result = db.query(AnalyticsResult).filter(
        AnalyticsResult.company_id == company_id,
        AnalyticsResult.analysis_type == "full_analysis",
    ).order_by(AnalyticsResult.created_at.desc()).first()
    if not result:
        run_company_analytics(company_id)
        result = db.query(AnalyticsResult).filter(
            AnalyticsResult.company_id == company_id,
            AnalyticsResult.analysis_type == "full_analysis",
        ).first()
    if not result:
        return {"message": "No data available", "data": {}}
    return json.loads(result.result_json)


@router.post("/company/{company_id}/run")
def trigger_analytics(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner, UserRole.company_admin])),
):
    if not _can_access(current_user, company_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    run_company_analytics(company_id, user_id=current_user.id)
    return {"message": "Analytics completed"}


@router.get("/benchmark")
def benchmark(
    industry: Optional[str] = Query(None),
    company_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = get_benchmarking(db, industry=industry)
    benchmarks = data["benchmarks"]
    if company_ids:
        ids = [int(x) for x in company_ids.split(",")]
        benchmarks = [b for b in benchmarks if b["company_id"] in ids]
    if current_user.role != UserRole.platform_owner:
        benchmarks = [b for b in benchmarks if b["company_id"] == current_user.company_id]
    return {"benchmarks": benchmarks}


@router.get("/results", response_model=list[AnalyticsResultResponse])
def list_results(
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(AnalyticsResult)
    if current_user.role != UserRole.platform_owner:
        query = query.filter(AnalyticsResult.company_id == current_user.company_id)
    elif company_id:
        query = query.filter(AnalyticsResult.company_id == company_id)
    return query.order_by(AnalyticsResult.created_at.desc()).limit(50).all()


@router.get("/system-health", response_model=SystemHealthResponse)
def system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.platform_owner])),
):
    from app.models import AnnualReport
    pending_ext = db.query(AnnualReport).filter(
        AnnualReport.status.in_([ReportStatus.pending, ReportStatus.processing])
    ).count()
    failed_ext = db.query(AnnualReport).filter(AnnualReport.status == ReportStatus.failed).count()
    pending_jobs = db.query(BackgroundJob).filter(BackgroundJob.status == JobStatus.pending).count()
    alerts = []
    if failed_ext >= settings.alert_failed_extractions_threshold:
        alerts.append(f"{failed_ext} failed extractions exceed threshold")
    if pending_ext >= settings.alert_pending_extractions_threshold:
        alerts.append(f"{pending_ext} pending extractions exceed threshold")
    return SystemHealthResponse(
        status="healthy" if not alerts else "degraded",
        database="connected",
        total_users=db.query(UserModel).count(),
        total_companies=db.query(Company).count(),
        total_reports=db.query(AnnualReport).count(),
        pending_extractions=pending_ext,
        failed_extractions=failed_ext,
        pending_jobs=pending_jobs,
        alerts=alerts,
    )


@router.get("/export/pdf")
def export_pdf(
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_access(current_user, company_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if current_user.role == UserRole.employee:
        raise HTTPException(status_code=403, detail="Export not permitted for employees")

    company = db.query(Company).filter(Company.id == company_id).first()
    result = db.query(AnalyticsResult).filter(
        AnalyticsResult.company_id == company_id,
        AnalyticsResult.analysis_type == "full_analysis",
    ).order_by(AnalyticsResult.created_at.desc()).first()
    data = json.loads(result.result_json) if result else {}

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50

    # Header / branding
    c.setFillColorRGB(0.1, 0.2, 0.5)
    c.rect(0, height - 70, width, 70, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, height - 45, "JSE Analytics Platform")
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 62, company.company_name)
    if company.jse_code:
        c.drawString(width - 150, height - 45, f"JSE: {company.jse_code}")

    c.setFillColorRGB(0, 0, 0)
    y = height - 100
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Executive Summary")
    y -= 22
    c.setFont("Helvetica", 11)
    for label, key in [
        ("Overall Score", "overall_score"),
        ("Financial Health", "financial_health_score"),
        ("Governance Score", "governance_score"),
        ("Risk Classification", "risk_classification"),
    ]:
        c.drawString(50, y, f"{label}: {data.get(key, 'N/A')}")
        y -= 16

    risk_factors = data.get("risk_factors") or []
    if risk_factors:
        y -= 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Risk Factors")
        y -= 18
        c.setFont("Helvetica", 10)
        for factor in risk_factors[:8]:
            c.drawString(60, y, f"• {str(factor)[:90]}")
            y -= 14

    gov_metrics = data.get("governance_metrics") or {}
    if gov_metrics:
        y -= 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Governance Categories")
        y -= 18
        c.setFont("Helvetica", 10)
        for cat, score in gov_metrics.items():
            c.drawString(60, y, f"{cat}: {score}")
            y -= 14
            if y < 80:
                c.showPage()
                y = height - 50

    trends = data.get("trends", {})
    if trends:
        y -= 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Year-on-Year Trends")
        y -= 18
        c.setFont("Helvetica", 10)
        for key, val in trends.items():
            c.drawString(60, y, f"{key.replace('_', ' ').title()}: {val}%")
            y -= 14

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 30, f"Generated by JSE Analytics Platform — {company.industry or 'N/A'} sector")
    c.showPage()
    c.save()
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=analytics_{company_id}.pdf"
    })


@router.get("/export/excel")
def export_excel(
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_access(current_user, company_id):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if current_user.role == UserRole.employee:
        raise HTTPException(status_code=403, detail="Export not permitted for employees")

    reports = db.query(AnnualReport).filter(AnnualReport.company_id == company_id).all()
    report_ids = [r.id for r in reports]

    wb = Workbook()
    ws_fin = wb.active
    ws_fin.title = "Financials"
    ws_fin.append(["Year", "Metric", "Value", "Category"])
    financials = db.query(ExtractedFinancial).filter(
        ExtractedFinancial.report_id.in_(report_ids)
    ).all() if report_ids else []
    for fin in financials:
        ws_fin.append([fin.financial_year, fin.metric_name, fin.metric_value, fin.category])

    ws_gov = wb.create_sheet("Governance")
    ws_gov.append(["Category", "Content", "Confidence"])
    narratives = db.query(GovernanceNarrative).filter(
        GovernanceNarrative.report_id.in_(report_ids)
    ).all() if report_ids else []
    for gov in narratives:
        ws_gov.append([gov.category, gov.content[:500], gov.confidence_score])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=analytics_{company_id}.xlsx"},
    )
