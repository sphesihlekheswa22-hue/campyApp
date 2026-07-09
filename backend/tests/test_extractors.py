from app.extraction.extractors import extract_financials_from_patterns, extract_financials_from_text, parse_monetary_value


def test_parse_monetary_value_billions():
    assert parse_monetary_value("1,234.5", "total revenue billion") == 1_234_500_000_000.0


def test_extract_financials_from_patterns():
    text = """
    GROUP FINANCIAL PERFORMANCE
    Total revenue for the year ended 30 June 2024 amounted to 12,450,000,000
    Profit for the year 1,250,000,000
    Total assets 45,000,000,000
    """
    results = extract_financials_from_patterns(text, "2024")
    names = {r["metric_name"] for r in results}
    assert "Revenue" in names
    assert "Profit" in names
    assert "Assets" in names


def test_extract_financials_multiline():
    text = "Total revenue\n12,500,000\nProfit for the year\n850,000"
    results = extract_financials_from_text(text, "2024")
    assert len(results) >= 1
