"""King IV and JSE Listings Requirements compliance mapping."""

from app.models import GovernanceNarrative

KING_IV_PRINCIPLES = [
    {"id": "king_iv_1", "framework": "King IV", "principle": "Ethical leadership and corporate citizenship", "maps_to": ["Board Structure", "Compliance"]},
    {"id": "king_iv_2", "framework": "King IV", "principle": "Board composition and independence", "maps_to": ["Board Structure"]},
    {"id": "king_iv_3", "framework": "King IV", "principle": "Board committees and delegation", "maps_to": ["Board Structure", "Risk Management"]},
    {"id": "king_iv_4", "framework": "King IV", "principle": "Governance of risk", "maps_to": ["Risk Management"]},
    {"id": "king_iv_5", "framework": "King IV", "principle": "Governance of IT and information", "maps_to": ["Risk Management", "Compliance"]},
    {"id": "king_iv_6", "framework": "King IV", "principle": "Compliance with laws and rules", "maps_to": ["Compliance"]},
    {"id": "king_iv_7", "framework": "King IV", "principle": "Stakeholder relationships", "maps_to": ["Sustainability", "Compliance"]},
    {"id": "king_iv_8", "framework": "King IV", "principle": "Integrated reporting and disclosure", "maps_to": ["Sustainability", "Compliance"]},
]

JSE_LISTINGS = [
    {"id": "jse_3_1", "framework": "JSE Listings", "principle": "Board composition and director independence", "maps_to": ["Board Structure"]},
    {"id": "jse_3_2", "framework": "JSE Listings", "principle": "Audit committee requirements", "maps_to": ["Board Structure", "Compliance"]},
    {"id": "jse_3_3", "framework": "JSE Listings", "principle": "Risk management disclosure", "maps_to": ["Risk Management"]},
    {"id": "jse_3_4", "framework": "JSE Listings", "principle": "Social and ethics committee", "maps_to": ["Sustainability", "Compliance"]},
    {"id": "jse_3_5", "framework": "JSE Listings", "principle": "Continued disclosure of material information", "maps_to": ["Compliance"]},
    {"id": "jse_3_6", "framework": "JSE Listings", "principle": "ESG and sustainability reporting", "maps_to": ["Sustainability"]},
]


def _category_scores(narratives: list[GovernanceNarrative]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for n in narratives:
        prev = scores.get(n.category, 0.0)
        score = round(n.confidence_score * 100, 1)
        if score > prev:
            scores[n.category] = score
    return scores


def evaluate_compliance(narratives: list[GovernanceNarrative]) -> dict:
    cat_scores = _category_scores(narratives)
    items = []

    for entry in KING_IV_PRINCIPLES + JSE_LISTINGS:
        mapped = entry["maps_to"]
        covered_scores = [cat_scores.get(c, 0) for c in mapped]
        best = max(covered_scores) if covered_scores else 0
        met = best >= 50
        items.append({
            "id": entry["id"],
            "framework": entry["framework"],
            "principle": entry["principle"],
            "categories": mapped,
            "score": best,
            "status": "met" if met else ("partial" if best > 0 else "not_met"),
        })

    met_count = sum(1 for i in items if i["status"] == "met")
    partial_count = sum(1 for i in items if i["status"] == "partial")
    total = len(items)

    return {
        "items": items,
        "summary": {
            "total": total,
            "met": met_count,
            "partial": partial_count,
            "not_met": total - met_count - partial_count,
            "compliance_pct": round((met_count + partial_count * 0.5) / total * 100, 1) if total else 0,
        },
        "category_scores": cat_scores,
    }
