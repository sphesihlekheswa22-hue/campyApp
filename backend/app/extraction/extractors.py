import re
from typing import Any

import pdfplumber

GOVERNANCE_KEYWORDS = {
    "Board Structure": ["board of directors", "board structure", "directors", "chairman", "governance structure"],
    "Risk Management": ["risk management", "risk assessment", "operational risk", "financial risk"],
    "Compliance": ["compliance", "regulatory", "legal requirements", "statutory"],
    "Sustainability": ["sustainability", "environmental", "esg", "carbon", "social responsibility"],
}

FINANCIAL_METRICS = {
    "Revenue": ["revenue", "turnover", "sales"],
    "Profit": ["profit", "net income", "earnings"],
    "Assets": ["total assets", "assets"],
    "Liabilities": ["total liabilities", "liabilities"],
    "Equity": ["total equity", "shareholders equity", "equity"],
}


def extract_text_from_pdf(file_path: str) -> str:
    text_parts = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        print(f"[EXTRACTION] pdfplumber error: {e}")
    return "\n".join(text_parts)


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
                    for raw_table in page.extract_tables() or []:
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


def extract_financials_from_text(text: str, financial_year: str) -> list[dict]:
    results = []
    lines = text.split("\n")
    for line in lines:
        line_lower = line.lower()
        for metric_name, keywords in FINANCIAL_METRICS.items():
            for keyword in keywords:
                if keyword in line_lower:
                    numbers = re.findall(r"[\d,]+\.?\d*", line)
                    if numbers:
                        try:
                            value = float(numbers[-1].replace(",", ""))
                            if value > 0:
                                results.append({
                                    "financial_year": financial_year,
                                    "metric_name": metric_name,
                                    "metric_value": value,
                                    "category": "Financial Statements",
                                })
                                break
                        except ValueError:
                            pass
    return results


def extract_financials_from_tables(tables: list[Any], financial_year: str) -> list[dict]:
    results = []
    for df in tables:
        try:
            for _, row in df.iterrows():
                row_text = " ".join(str(v).lower() for v in row.values)
                for metric_name, keywords in FINANCIAL_METRICS.items():
                    if any(kw in row_text for kw in keywords):
                        for val in row.values:
                            val_str = str(val).replace(",", "").strip()
                            if re.match(r"^\d+\.?\d*$", val_str):
                                results.append({
                                    "financial_year": financial_year,
                                    "metric_name": metric_name,
                                    "metric_value": float(val_str),
                                    "category": "Financial Statements",
                                })
                                break
        except Exception:
            continue
    return results


def extract_governance_narratives(text: str) -> list[dict]:
    results = []
    paragraphs = re.split(r"\n\s*\n", text)
    for category, keywords in GOVERNANCE_KEYWORDS.items():
        best_match = ""
        best_score = 0.0
        for para in paragraphs:
            para_lower = para.lower()
            matches = sum(1 for kw in keywords if kw in para_lower)
            if matches > 0:
                score = min(1.0, matches / len(keywords) + len(para) / 2000)
                if score > best_score:
                    best_score = score
                    best_match = para.strip()[:2000]
        if best_match:
            results.append({
                "category": category,
                "content": best_match,
                "confidence_score": round(best_score, 2),
            })
    return results


def detect_financial_year(text: str) -> str:
    years = re.findall(r"20\d{2}", text)
    if years:
        return years[-1]
    from datetime import datetime
    return str(datetime.now().year)
