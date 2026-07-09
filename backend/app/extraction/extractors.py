import re
from typing import Any

import pdfplumber

GOVERNANCE_KEYWORDS = {
    "Board Structure": ["board of directors", "board structure", "directors", "chairman", "governance structure", "king iv"],
    "Risk Management": ["risk management", "risk assessment", "operational risk", "financial risk", "risk committee"],
    "Compliance": ["compliance", "regulatory", "legal requirements", "statutory", "jse listings"],
    "Sustainability": ["sustainability", "environmental", "esg", "carbon", "social responsibility", "climate"],
}

FINANCIAL_METRICS = {
    "Revenue": ["revenue", "turnover", "sales", "total income", "total revenue", "group revenue"],
    "Profit": [
        "profit for the year", "profit attributable", "net income", "earnings", "profit after tax",
        "net profit", "profit/(loss)", "loss for the year", "total comprehensive income",
    ],
    "Assets": ["total assets", "assets total", "total group assets"],
    "Liabilities": ["total liabilities", "liabilities total", "total group liabilities"],
    "Equity": ["total equity", "shareholders equity", "shareholders' equity", "total shareholders", "shareholders' funds"],
}

MONETARY_SUFFIX = {
    "billion": 1_000_000_000,
    "bn": 1_000_000_000,
    "million": 1_000_000,
    "m": 1_000_000,
    "thousand": 1_000,
    "k": 1_000,
}


def parse_monetary_value(raw: str, line_context: str = "") -> float | None:
    """Parse numbers from JSE-style reports including R/m/bn suffixes."""
    if not raw:
        return None
    cleaned = raw.strip().replace("\u00a0", " ").replace("R", "").replace("ZAR", "").strip()
    cleaned = cleaned.replace("(", "-").replace(")", "")
    context = (line_context + " " + cleaned).lower()

    multiplier = 1.0
    for suffix, mult in MONETARY_SUFFIX.items():
        if re.search(rf"\b{suffix}\b", context):
            multiplier = mult
            break

    match = re.search(r"-?[\d,]+\.?\d*", cleaned)
    if not match:
        return None
    try:
        value = float(match.group().replace(",", ""))
    except ValueError:
        return None

    if value == 0:
        return None
    if multiplier == 1.0 and abs(value) < 1000 and any(s in context for s in ("million", "m ", " bn")):
        multiplier = 1_000_000
    return round(value * multiplier, 2)


def _extract_with_pdfplumber(file_path: str) -> str:
    text_parts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
                if page_text:
                    text_parts.append(page_text)
                    continue
                words = page.extract_words(x_tolerance=2, y_tolerance=2) or []
                if words:
                    lines: dict[int, list[str]] = {}
                    for word in words:
                        top = int(word.get("top", 0))
                        lines.setdefault(top, []).append(word.get("text", ""))
                    page_text = "\n".join(
                        " ".join(lines[key]) for key in sorted(lines.keys())
                    )
                    if page_text.strip():
                        text_parts.append(page_text)
    except Exception as e:
        print(f"[EXTRACTION] pdfplumber error: {e}")
    return "\n".join(text_parts)


def extract_text_with_pymupdf(file_path: str) -> str:
    """Fallback text extraction — works well on many JSE PDFs when pdfplumber returns little."""
    try:
        import fitz
        doc = fitz.open(file_path)
        parts = [page.get_text("text") for page in doc]
        doc.close()
        return "\n".join(parts)
    except Exception as e:
        print(f"[EXTRACTION] pymupdf error: {e}")
        return ""


def extract_text_from_pdf(file_path: str) -> str:
    text = _extract_with_pdfplumber(file_path)

    if len(text.strip()) < 100:
        pymupdf_text = extract_text_with_pymupdf(file_path)
        if len(pymupdf_text.strip()) > len(text.strip()):
            text = pymupdf_text

    if len(text.strip()) < 100:
        ocr_text = extract_text_with_ocr(file_path)
        if ocr_text:
            text = ocr_text
    return text


def extract_text_with_ocr(file_path: str) -> str:
    """OCR fallback for scanned PDFs — requires pdf2image + pytesseract if enabled."""
    from app.config import get_settings
    cfg = get_settings()
    if not cfg.ocr_enabled:
        return ""
    try:
        from pdf2image import convert_from_path
        import pytesseract
        images = convert_from_path(file_path, dpi=200, first_page=1, last_page=5)
        parts = [pytesseract.image_to_string(img) for img in images]
        return "\n".join(parts)
    except Exception as e:
        print(f"[EXTRACTION] OCR unavailable: {e}")
        return ""


def extract_tables_from_pdf(file_path: str) -> list[Any]:
    tables = []
    try:
        import camelot
        camelot_tables = camelot.read_pdf(file_path, pages="all", flavor="stream")
        for table in camelot_tables:
            tables.append(table.df)
    except Exception as e:
        print(f"[EXTRACTION] Camelot unavailable: {e}")

    if not tables:
        try:
            import pandas as pd
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    for strategy in ("lines", "text"):
                        try:
                            raw_tables = page.extract_tables(table_settings={"vertical_strategy": strategy, "horizontal_strategy": strategy}) or []
                        except TypeError:
                            raw_tables = page.extract_tables() or []
                        for raw_table in raw_tables:
                            if not raw_table or len(raw_table) < 2:
                                continue
                            header = raw_table[0]
                            rows = raw_table[1:]
                            if header and any(header):
                                df = pd.DataFrame(rows, columns=header)
                            else:
                                df = pd.DataFrame(rows)
                            tables.append(df)
        except Exception as e:
            print(f"[EXTRACTION] pdfplumber tables error: {e}")
    return tables


def _metric_from_line(line: str, financial_year: str) -> list[dict]:
    results = []
    line_lower = line.lower()
    for metric_name, keywords in FINANCIAL_METRICS.items():
        matched = False
        for keyword in sorted(keywords, key=len, reverse=True):
            if keyword in line_lower:
                matched = True
                break
        if not matched:
            continue
        numbers = re.findall(r"[\(\)\-]?[\d,]+\.?\d*", line)
        if not numbers:
            continue
        for num in reversed(numbers):
            value = parse_monetary_value(num, line)
            if value is not None and abs(value) > 0:
                results.append({
                    "financial_year": financial_year,
                    "metric_name": metric_name,
                    "metric_value": abs(value),
                    "category": "Financial Statements",
                })
                break
    return results


def extract_financials_from_text(text: str, financial_year: str) -> list[dict]:
    results = []
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    for line in lines:
        if len(line) < 4:
            continue
        results.extend(_metric_from_line(line, financial_year))

    # Multi-line: metric label on one line, value on the next
    for i, line in enumerate(lines):
        combined = line
        if i + 1 < len(lines):
            combined = f"{line} {lines[i + 1]}"
        if i + 2 < len(lines):
            combined_long = f"{line} {lines[i + 1]} {lines[i + 2]}"
            results.extend(_metric_from_line(combined_long, financial_year))
        results.extend(_metric_from_line(combined, financial_year))

    results.extend(extract_financials_from_patterns(text, financial_year))
    return _dedupe_financials(results)


def extract_financials_from_patterns(text: str, financial_year: str) -> list[dict]:
    """Regex pass for common JSE annual report phrasing."""
    results = []
    normalized = re.sub(r"\s+", " ", text.lower())
    pattern_map = [
        (r"(?:total\s+)?(?:group\s+)?revenue[^\d]{0,60}([\(\)\-\d,\.]+)", "Revenue"),
        (r"turnover[^\d]{0,60}([\(\)\-\d,\.]+)", "Revenue"),
        (r"(?:profit|loss)\s+for\s+the\s+year[^\d]{0,60}([\(\)\-\d,\.]+)", "Profit"),
        (r"net\s+(?:profit|income)[^\d]{0,60}([\(\)\-\d,\.]+)", "Profit"),
        (r"total\s+assets[^\d]{0,60}([\(\)\-\d,\.]+)", "Assets"),
        (r"total\s+liabilities[^\d]{0,60}([\(\)\-\d,\.]+)", "Liabilities"),
        (r"total\s+equity[^\d]{0,60}([\(\)\-\d,\.]+)", "Equity"),
    ]
    for pattern, metric_name in pattern_map:
        for match in re.finditer(pattern, normalized, re.IGNORECASE):
            value = parse_monetary_value(match.group(1), match.group(0))
            if value is not None and abs(value) > 0:
                results.append({
                    "financial_year": financial_year,
                    "metric_name": metric_name,
                    "metric_value": abs(value),
                    "category": "Financial Statements",
                })
    return results


def _dedupe_financials(items: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict] = []
    for item in items:
        key = (item["metric_name"], item["financial_year"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def extract_financials_from_tables(tables: list[Any], financial_year: str) -> list[dict]:
    results = []
    for df in tables:
        try:
            cols = list(df.columns)
            for _, row in df.iterrows():
                row_values = [str(v) for v in row.values if str(v).strip() and str(v) != "nan"]
                if not row_values:
                    continue
                label = row_values[0].lower()
                for metric_name, keywords in FINANCIAL_METRICS.items():
                    if not any(kw in label for kw in keywords):
                        continue
                    for val in reversed(row_values[1:] + cols[1:]):
                        parsed = parse_monetary_value(str(val), label)
                        if parsed is not None and parsed > 0:
                            results.append({
                                "financial_year": financial_year,
                                "metric_name": metric_name,
                                "metric_value": parsed,
                                "category": "Financial Statements",
                            })
                            break
        except Exception:
            continue
    return results


def extract_governance_narratives(text: str) -> list[dict]:
    results = []
    paragraphs = re.split(r"\n\s*\n", text)
    min_para_len = 40 if len(text.strip()) < 5000 else 80
    for category, keywords in GOVERNANCE_KEYWORDS.items():
        best_match = ""
        best_score = 0.0
        for para in paragraphs:
            if len(para.strip()) < min_para_len:
                continue
            para_lower = para.lower()
            matches = sum(1 for kw in keywords if kw in para_lower)
            if matches > 0:
                score = min(1.0, (matches / max(len(keywords), 1)) * 0.6 + min(len(para), 1500) / 2000 * 0.4)
                if score > best_score:
                    best_score = score
                    best_match = para.strip()[:2000]
        if best_match:
            results.append({
                "category": category,
                "content": best_match,
                "confidence_score": round(max(0.35, best_score), 2),
            })
    return results


def detect_financial_year(text: str) -> str:
    patterns = [
        r"financial year ended?\s+\d{1,2}\s+\w+\s+(20\d{2})",
        r"for the year ended?\s+\d{1,2}\s+\w+\s+(20\d{2})",
        r"annual report\s+(20\d{2})",
        r"fy\s*(20\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    years = re.findall(r"20\d{2}", text)
    if years:
        from collections import Counter
        return Counter(years).most_common(1)[0][0]
    from datetime import datetime
    return str(datetime.now().year)
