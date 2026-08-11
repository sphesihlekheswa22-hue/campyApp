from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import false, or_
from sqlalchemy.orm import Session

from app.auth.security import get_current_user
from app.database.session import get_db
from app.models import AnnualReport, Company, User, UserRole

router = APIRouter(prefix="/search", tags=["search"])


def _result(type_: str, title: str, href: str, subtitle: str = "", id_: Optional[int] = None) -> dict[str, Any]:
    item = {"type": type_, "title": title, "subtitle": subtitle, "href": href}
    if id_ is not None:
        item["id"] = id_
    return item


@router.get("/")
def global_search(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Role-scoped jump search across companies, reports, and users."""
    term = q.strip()
    if not term:
        return {"query": q, "results": []}

    like = f"%{term}%"
    results: list[dict[str, Any]] = []
    is_owner = current_user.role == UserRole.platform_owner
    is_admin = current_user.role == UserRole.company_admin
    company_id = current_user.company_id

    # Companies
    company_q = db.query(Company)
    if not is_owner:
        if not company_id:
            company_q = company_q.filter(false())
        else:
            company_q = company_q.filter(Company.id == company_id)
    company_q = company_q.filter(
        or_(
            Company.company_name.ilike(like),
            Company.registration_number.ilike(like),
            Company.industry.ilike(like),
            Company.jse_code.ilike(like),
            Company.sector.ilike(like),
        )
    ).order_by(Company.company_name).limit(limit)
    for c in company_q.all():
        subtitle_parts = [p for p in [c.jse_code, c.industry or c.sector] if p]
        results.append(
            _result(
                "company",
                c.company_name,
                f"/companies/detail.html?id={c.id}",
                " · ".join(subtitle_parts) or "Company",
                c.id,
            )
        )

    # Reports
    report_q = db.query(AnnualReport)
    if not is_owner:
        if not company_id:
            report_q = report_q.filter(false())
        else:
            report_q = report_q.filter(AnnualReport.company_id == company_id)
    report_filters = [AnnualReport.file_path.ilike(like)]
    if term.isdigit():
        report_filters.append(AnnualReport.id == int(term))
    report_q = report_q.filter(or_(*report_filters)).order_by(AnnualReport.upload_date.desc()).limit(limit)
    for r in report_q.all():
        filename = (r.file_path or "").split("/")[-1] or f"Report #{r.id}"
        results.append(
            _result(
                "report",
                filename,
                f"/reports/detail.html?id={r.id}",
                f"Report #{r.id} · {r.status.value if hasattr(r.status, 'value') else r.status}",
                r.id,
            )
        )

    # Users (owners + company admins only)
    if is_owner or is_admin:
        user_q = db.query(User)
        if is_admin:
            user_q = user_q.filter(User.company_id == company_id)
        user_q = user_q.filter(
            or_(
                User.name.ilike(like),
                User.surname.ilike(like),
                User.email.ilike(like),
            )
        ).order_by(User.name).limit(limit)
        for u in user_q.all():
            results.append(
                _result(
                    "user",
                    f"{u.name} {u.surname}".strip(),
                    "/team/index.html",
                    u.email or (u.role.value if hasattr(u.role, "value") else str(u.role)),
                    u.id,
                )
            )

    return {"query": term, "results": results[:24]}
