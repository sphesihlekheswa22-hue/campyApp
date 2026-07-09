import json
from datetime import datetime, timedelta, timezone
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.config import get_settings
from app.database.session import SessionLocal
from app.models import AnalyticsResult, Company, ScheduledReport, User
from app.services.email_service import send_email

settings = get_settings()


def _build_summary_pdf(company: Company, data: dict) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, f"Monthly Summary — {company.company_name}")
    y -= 28
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    y -= 24
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Executive Summary")
    y -= 18
    c.setFont("Helvetica", 11)
    for label, key in [
        ("Overall Score", "overall_score"),
        ("Financial Health", "financial_health_score"),
        ("Governance Score", "governance_score"),
        ("Risk Level", "risk_classification"),
    ]:
        c.drawString(50, y, f"{label}: {data.get(key, 'N/A')}")
        y -= 14
    risk_factors = data.get("risk_factors") or []
    if risk_factors:
        y -= 8
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Risk Factors")
        y -= 16
        c.setFont("Helvetica", 10)
        for factor in risk_factors[:6]:
            c.drawString(60, y, f"• {factor[:80]}")
            y -= 12
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()


def send_scheduled_report(schedule_id: int) -> None:
    db = SessionLocal()
    try:
        schedule = db.query(ScheduledReport).filter(ScheduledReport.id == schedule_id).first()
        if not schedule or not schedule.is_active:
            return

        user = db.query(User).filter(User.id == schedule.user_id).first()
        company = db.query(Company).filter(Company.id == schedule.company_id).first()
        if not user or not company:
            return

        result = db.query(AnalyticsResult).filter(
            AnalyticsResult.company_id == company.id,
            AnalyticsResult.analysis_type == "full_analysis",
        ).order_by(AnalyticsResult.created_at.desc()).first()
        data = json.loads(result.result_json) if result else {}

        body = (
            f"Your scheduled {schedule.frequency} analytics summary for {company.company_name}.\n\n"
            f"Overall Score: {data.get('overall_score', 'N/A')}\n"
            f"Financial Health: {data.get('financial_health_score', 'N/A')}\n"
            f"Governance: {data.get('governance_score', 'N/A')}\n"
            f"Risk: {data.get('risk_classification', 'N/A')}\n\n"
            f"View full dashboard: {settings.app_url}/analytics/index.html"
        )
        send_email(user.email, f"JSE Analytics — {company.company_name} Monthly Summary", body)

        schedule.last_sent_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def due_schedules(db) -> list[ScheduledReport]:
    """Return active schedules due for sending based on frequency."""
    now = datetime.now(timezone.utc)
    schedules = db.query(ScheduledReport).filter(ScheduledReport.is_active == True).all()
    due = []
    for s in schedules:
        if not s.last_sent_at:
            due.append(s)
            continue
        delta = {
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
            "monthly": timedelta(days=30),
        }.get(s.frequency, timedelta(days=30))
        if s.last_sent_at + delta <= now:
            due.append(s)
    return due
