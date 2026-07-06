import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from app.database.session import SessionLocal
from app.models import AnalyticsResult, AnnualReport, Company, ExtractedFinancial, GovernanceNarrative

MODEL_PATH = os.path.join(os.path.dirname(__file__), "risk_model.joblib")


def _train_or_load_model() -> RandomForestClassifier:
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)

    np.random.seed(42)
    X = np.random.rand(100, 5) * 100
    y = np.random.choice(["low", "medium", "high"], 100)
    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X, y)
    joblib.dump(model, MODEL_PATH)
    return model


def calculate_growth(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return round(((current - previous) / previous) * 100, 2)


def compute_financial_health_score(metrics: dict) -> float:
    revenue = metrics.get("Revenue", 0)
    profit = metrics.get("Profit", 0)
    assets = metrics.get("Assets", 0)
    liabilities = metrics.get("Liabilities", 0)
    equity = metrics.get("Equity", 0)

    profitability = (profit / revenue * 100) if revenue > 0 else 0
    leverage = (liabilities / assets * 100) if assets > 0 else 100
    equity_ratio = (equity / assets * 100) if assets > 0 else 0

    score = (
        min(profitability, 30) * 0.4
        + max(0, 30 - leverage) * 0.3
        + min(equity_ratio, 40) * 0.3
    )
    return round(min(100, max(0, score * 2)), 1)


def compute_governance_score(narratives: list) -> float:
    if not narratives:
        return 0.0
    categories = {"Board Structure", "Risk Management", "Compliance", "Sustainability"}
    covered = {n.category for n in narratives}
    coverage = len(covered & categories) / len(categories)
    avg_confidence = sum(n.confidence_score for n in narratives) / len(narratives)
    return round(coverage * 50 + avg_confidence * 50, 1)


def classify_risk(financial_score: float, governance_score: float, metrics: dict) -> str:
    combined = financial_score * 0.6 + governance_score * 0.4
    leverage = metrics.get("Liabilities", 0) / max(metrics.get("Assets", 1), 1) * 100
    if combined >= 70 and leverage < 60:
        return "low"
    if combined >= 45:
        return "medium"
    return "high"


def run_company_analytics(company_id: int) -> None:
    db = SessionLocal()
    try:
        reports = db.query(AnnualReport).filter(AnnualReport.company_id == company_id).all()
        report_ids = [r.id for r in reports]
        if not report_ids:
            return

        financials = db.query(ExtractedFinancial).filter(
            ExtractedFinancial.report_id.in_(report_ids)
        ).all()
        narratives = db.query(GovernanceNarrative).filter(
            GovernanceNarrative.report_id.in_(report_ids)
        ).all()

        metrics_by_year: dict[str, dict[str, float]] = {}
        for fin in financials:
            metrics_by_year.setdefault(fin.financial_year, {})[fin.metric_name] = fin.metric_value

        years = sorted(metrics_by_year.keys())
        trends = {}
        if len(years) >= 2:
            prev, curr = metrics_by_year[years[-2]], metrics_by_year[years[-1]]
            trends = {
                "revenue_growth": calculate_growth(curr.get("Revenue", 0), prev.get("Revenue", 0)),
                "profit_growth": calculate_growth(curr.get("Profit", 0), prev.get("Profit", 0)),
                "asset_growth": calculate_growth(curr.get("Assets", 0), prev.get("Assets", 0)),
            }

        current_metrics = metrics_by_year.get(years[-1], {}) if years else {}
        financial_score = compute_financial_health_score(current_metrics)
        governance_score = compute_governance_score(narratives)
        overall_score = round(financial_score * 0.6 + governance_score * 0.4, 1)
        risk = classify_risk(financial_score, governance_score, current_metrics)

        governance_metrics = {}
        for narrative in narratives:
            governance_metrics[narrative.category] = round(narrative.confidence_score * 100, 1)

        results = {
            "trends": trends,
            "years": years,
            "metrics_by_year": metrics_by_year,
            "financial_health_score": financial_score,
            "governance_score": governance_score,
            "governance_metrics": governance_metrics,
            "overall_score": overall_score,
            "risk_classification": risk,
        }

        db.query(AnalyticsResult).filter(
            AnalyticsResult.company_id == company_id,
            AnalyticsResult.analysis_type == "full_analysis",
        ).delete()

        db.add(AnalyticsResult(
            company_id=company_id,
            analysis_type="full_analysis",
            result_json=json.dumps(results),
        ))
        db.commit()
    finally:
        db.close()


def get_benchmarking(db, company_id: int | None = None) -> dict:
    companies = db.query(Company).all()
    benchmarks = []
    for company in companies:
        if company_id and company.id != company_id:
            continue
        result = db.query(AnalyticsResult).filter(
            AnalyticsResult.company_id == company.id,
            AnalyticsResult.analysis_type == "full_analysis",
        ).order_by(AnalyticsResult.created_at.desc()).first()
        if result:
            data = json.loads(result.result_json)
            benchmarks.append({
                "company_id": company.id,
                "company_name": company.company_name,
                "industry": company.industry,
                "financial_health_score": data.get("financial_health_score", 0),
                "governance_score": data.get("governance_score", 0),
                "overall_score": data.get("overall_score", 0),
                "risk_classification": data.get("risk_classification", "medium"),
                "revenue": data.get("metrics_by_year", {}).get(
                    sorted(data.get("years", []))[-1] if data.get("years") else "", {}
                ).get("Revenue", 0),
            })
    return {"benchmarks": benchmarks}
