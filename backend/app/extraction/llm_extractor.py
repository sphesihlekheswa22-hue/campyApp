"""Optional LLM-assisted governance extraction when OPENAI_API_KEY is set."""

import json
import urllib.error
import urllib.request

from app.config import get_settings

settings = get_settings()

GOVERNANCE_CATEGORIES = [
    "Board Structure",
    "Risk Management",
    "Compliance",
    "Sustainability",
]


def extract_governance_with_llm(text: str) -> list[dict]:
    if not settings.openai_api_key or len(text.strip()) < 200:
        return []

    excerpt = text[:12000]
    prompt = (
        "Extract governance narratives from this JSE annual report excerpt. "
        "Return JSON array with objects: category (one of Board Structure, Risk Management, Compliance, Sustainability), "
        "content (relevant paragraph, max 500 chars), confidence_score (0.0-1.0). "
        "Only include categories with real evidence.\n\n"
        f"TEXT:\n{excerpt}"
    )

    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": "You are a JSE corporate governance analyst. Respond with valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        items = parsed if isinstance(parsed, list) else parsed.get("narratives") or parsed.get("items") or []
        results = []
        for item in items:
            cat = item.get("category", "")
            if cat not in GOVERNANCE_CATEGORIES:
                continue
            results.append({
                "category": cat,
                "content": str(item.get("content", ""))[:2000],
                "confidence_score": min(1.0, max(0.0, float(item.get("confidence_score", 0.7)))),
            })
        return results
    except (urllib.error.HTTPError, KeyError, json.JSONDecodeError, ValueError) as e:
        print(f"[LLM EXTRACTION] Skipped: {e}")
        return []
