"""AI assistant chat — grounded in company analytics and compliance data."""

import json
import urllib.error
import urllib.request

from sqlalchemy.orm import Session

from app.compliance.checklist import evaluate_compliance
from app.config import get_settings
from app.models import AnalyticsResult, AnnualReport, Company, GovernanceNarrative, ReportStatus, User, UserRole

settings = get_settings()


def _can_access_company(user: User, company_id: int) -> bool:
    if user.role == UserRole.platform_owner:
        return True
    return user.company_id == company_id


def _resolve_company_id(user: User, company_id: int | None) -> int | None:
    if company_id is not None:
        return company_id if _can_access_company(user, company_id) else None
    if user.company_id:
        return user.company_id
    return None


def build_company_context(db: Session, company_id: int) -> dict:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return {}

    analytics = db.query(AnalyticsResult).filter(
        AnalyticsResult.company_id == company_id,
        AnalyticsResult.analysis_type == "full_analysis",
    ).order_by(AnalyticsResult.created_at.desc()).first()

    analytics_data = {}
    if analytics:
        try:
            analytics_data = json.loads(analytics.result_json)
        except json.JSONDecodeError:
            analytics_data = {}

    narratives = (
        db.query(GovernanceNarrative)
        .join(AnnualReport)
        .filter(AnnualReport.company_id == company_id)
        .all()
    )
    compliance = evaluate_compliance(narratives)

    reports = db.query(AnnualReport).filter(AnnualReport.company_id == company_id).all()
    report_summary = {
        "total": len(reports),
        "complete": sum(1 for r in reports if r.status == ReportStatus.complete),
        "processing": sum(1 for r in reports if r.status in (ReportStatus.pending, ReportStatus.processing)),
        "failed": sum(1 for r in reports if r.status == ReportStatus.failed),
    }

    gaps = [
        {"principle": i["principle"], "framework": i["framework"], "status": i["status"]}
        for i in compliance.get("items", [])
        if i.get("status") != "met"
    ][:8]

    return {
        "company_name": company.company_name,
        "industry": company.industry,
        "jse_code": company.jse_code,
        "sector": company.sector,
        "subscription_status": company.subscription_status.value if company.subscription_status else None,
        "overall_score": analytics_data.get("overall_score"),
        "financial_health_score": analytics_data.get("financial_health_score"),
        "governance_score": analytics_data.get("governance_score"),
        "risk_classification": analytics_data.get("risk_classification"),
        "risk_factors": analytics_data.get("risk_factors", []),
        "years": analytics_data.get("years", []),
        "metrics_by_year": analytics_data.get("metrics_by_year", {}),
        "trends": analytics_data.get("trends", {}),
        "governance_metrics": analytics_data.get("governance_metrics", {}),
        "compliance_pct": compliance.get("summary", {}).get("compliance_pct"),
        "compliance_gaps": gaps,
        "reports": report_summary,
    }


def chat_reply(
    db: Session,
    user: User,
    message: str,
    company_id: int | None = None,
    history: list[dict] | None = None,
) -> str:
    if not settings.openai_api_key:
        return (
            "AI assistant is not configured on this server. "
            "Ask your administrator to set OPENAI_API_KEY."
        )

    resolved_id = _resolve_company_id(user, company_id)
    context_block = ""
    if resolved_id:
        ctx = build_company_context(db, resolved_id)
        if ctx:
            context_block = f"\n\nCOMPANY CONTEXT (use only this data):\n{json.dumps(ctx, indent=2)}"
    elif user.role == UserRole.platform_owner:
        context_block = (
            "\n\nThe user is a platform owner with no company selected. "
            "Answer general questions about JSE Analytics, King IV, and JSE compliance. "
            "For company-specific metrics, suggest opening a company profile first."
        )
    else:
        context_block = "\n\nNo company data is available for this user yet."

    system = (
        "You are the JSE Analytics AI Assistant on the Bluemachines platform. "
        "Help users understand financial health scores, governance, risk, compliance (King IV & JSE Listings), "
        "and annual report analytics for South African listed companies. "
        "Use ONLY the provided company context when answering company-specific questions. "
        "If data is missing, say so clearly — do not invent numbers. "
        "Keep answers concise (2–4 short paragraphs max), professional, and actionable."
        f"{context_block}"
    )

    messages = [{"role": "system", "content": system}]
    for item in (history or [])[-6:]:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content[:2000]})
    messages.append({"role": "user", "content": message.strip()[:4000]})

    payload = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 800,
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[CHAT] OpenAI HTTP error: {e.code} {err_body[:200]}")
        return "Sorry, the AI service returned an error. Please try again in a moment."
    except (KeyError, json.JSONDecodeError, urllib.error.URLError) as e:
        print(f"[CHAT] Error: {e}")
        return "Sorry, I couldn't reach the AI service. Please try again later."
