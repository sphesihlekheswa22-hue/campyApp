"""Seed database with platform owner, demo companies, reports, analytics, and audit logs."""
import argparse
import os
from datetime import date, datetime, timedelta, timezone

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.analytics.engine import run_company_analytics
from app.auth.security import hash_password
from app.config import get_settings
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models import (
    AnalyticsResult,
    AnnualReport,
    AuditLog,
    BackgroundJob,
    Company,
    ExtractedFinancial,
    GovernanceNarrative,
    JobStatus,
    Notification,
    NotificationType,
    PasswordResetToken,
    RegistrationPin,
    ScheduledReport,
    SubscriptionStatus,
    User,
    UserRole,
    EmailVerification,
    ReportStatus,
)

DEFAULT_PASSWORD = "Password123!"

GOVERNANCE_TEMPLATES = [
    (
        "Board Structure",
        "The board comprises nine directors, including three independent non-executive directors. "
        "Board committees include audit, risk, and remuneration committees with clearly defined charters.",
        0.92,
    ),
    (
        "Risk Management",
        "Enterprise risk management framework is reviewed annually. Key risks include market volatility, "
        "cybersecurity, and regulatory compliance. Mitigation strategies are documented and monitored quarterly.",
        0.88,
    ),
    (
        "Compliance",
        "The company maintains compliance with JSE listing requirements, Companies Act, and applicable "
        "industry regulations. Internal audit reports no material non-compliance in the reporting period.",
        0.85,
    ),
    (
        "Sustainability",
        "ESG commitments include net-zero targets by 2040, diversity initiatives, and community investment "
        "programs. Sustainability metrics are disclosed in the integrated annual report.",
        0.90,
    ),
]

# Richer demo set: JSE-style companies with metadata, multi-year financials, mixed statuses.
COMPANY_SEED = [
    {
        "company_name": "Blue Machines Ltd",
        "registration_number": "BM-2020-001",
        "website": "https://bluemachines.co.za",
        "industry": "Technology",
        "jse_code": "BLU",
        "sector": "Software & IT Services",
        "listing_date": date(2020, 6, 15),
        "market_cap": 2_400_000_000,
        "subscription_status": SubscriptionStatus.active,
        "admin": {"email": "admin@bluemachines.co.za", "name": "Sarah", "surname": "Ndlovu"},
        "employees": [
            {"email": "john.doe@bluemachines.co.za", "name": "John", "surname": "Doe"},
            {"email": "jane.smith@bluemachines.co.za", "name": "Jane", "surname": "Smith"},
            {"email": "peter.mokoena@bluemachines.co.za", "name": "Peter", "surname": "Mokoena"},
        ],
        "years": {
            "2021": {"Revenue": 38_000_000, "Profit": 2_100_000, "Assets": 98_000_000, "Liabilities": 40_000_000, "Equity": 58_000_000},
            "2022": {"Revenue": 45_000_000, "Profit": 3_200_000, "Assets": 120_000_000, "Liabilities": 45_000_000, "Equity": 75_000_000},
            "2023": {"Revenue": 52_000_000, "Profit": 4_100_000, "Assets": 135_000_000, "Liabilities": 48_000_000, "Equity": 87_000_000},
            "2024": {"Revenue": 61_000_000, "Profit": 5_400_000, "Assets": 148_000_000, "Liabilities": 50_000_000, "Equity": 98_000_000},
        },
        "extra_reports": 2,
        "failed_reports": 1,
    },
    {
        "company_name": "Naspers Limited",
        "registration_number": "NPN-1915-001",
        "website": "https://www.naspers.com",
        "industry": "Media",
        "jse_code": "NPN",
        "sector": "Media & Entertainment",
        "listing_date": date(1994, 9, 12),
        "market_cap": 680_000_000_000,
        "subscription_status": SubscriptionStatus.active,
        "admin": {"email": "admin@naspers.co.za", "name": "William", "surname": "Joubert"},
        "employees": [
            {"email": "analyst@naspers.co.za", "name": "Lindiwe", "surname": "Khumalo"},
            {"email": "finance@naspers.co.za", "name": "Andre", "surname": "Botha"},
        ],
        "years": {
            "2021": {"Revenue": 165_000_000, "Profit": 19_500_000, "Assets": 390_000_000, "Liabilities": 90_000_000, "Equity": 300_000_000},
            "2022": {"Revenue": 180_000_000, "Profit": 22_000_000, "Assets": 420_000_000, "Liabilities": 95_000_000, "Equity": 325_000_000},
            "2023": {"Revenue": 195_000_000, "Profit": 24_500_000, "Assets": 445_000_000, "Liabilities": 98_000_000, "Equity": 347_000_000},
            "2024": {"Revenue": 210_000_000, "Profit": 27_800_000, "Assets": 470_000_000, "Liabilities": 100_000_000, "Equity": 370_000_000},
        },
        "extra_reports": 1,
        "failed_reports": 0,
    },
    {
        "company_name": "Sasol Limited",
        "registration_number": "SOL-1950-001",
        "website": "https://www.sasol.com",
        "industry": "Energy",
        "jse_code": "SOL",
        "sector": "Oil, Gas & Chemicals",
        "listing_date": date(1979, 10, 1),
        "market_cap": 95_000_000_000,
        "subscription_status": SubscriptionStatus.trial,
        "admin": {"email": "admin@sasol.co.za", "name": "Thabo", "surname": "Molefe"},
        "employees": [
            {"email": "engineer@sasol.co.za", "name": "David", "surname": "Botha"},
            {"email": "esg@sasol.co.za", "name": "Zanele", "surname": "Mthembu"},
        ],
        "years": {
            "2021": {"Revenue": 340_000_000, "Profit": 21_000_000, "Assets": 600_000_000, "Liabilities": 300_000_000, "Equity": 300_000_000},
            "2022": {"Revenue": 320_000_000, "Profit": 18_000_000, "Assets": 580_000_000, "Liabilities": 310_000_000, "Equity": 270_000_000},
            "2023": {"Revenue": 295_000_000, "Profit": 12_500_000, "Assets": 560_000_000, "Liabilities": 320_000_000, "Equity": 240_000_000},
            "2024": {"Revenue": 310_000_000, "Profit": 15_200_000, "Assets": 575_000_000, "Liabilities": 315_000_000, "Equity": 260_000_000},
        },
        "extra_reports": 1,
        "failed_reports": 1,
    },
    {
        "company_name": "Standard Bank Group",
        "registration_number": "SBK-1862-001",
        "website": "https://www.standardbank.co.za",
        "industry": "Financial Services",
        "jse_code": "SBK",
        "sector": "Banks",
        "listing_date": date(1970, 1, 1),
        "market_cap": 310_000_000_000,
        "subscription_status": SubscriptionStatus.active,
        "admin": {"email": "admin@standardbank.co.za", "name": "Michelle", "surname": "van Wyk"},
        "employees": [
            {"email": "risk@standardbank.co.za", "name": "Sipho", "surname": "Dlamini"},
            {"email": "compliance@standardbank.co.za", "name": "Nomsa", "surname": "Zulu"},
            {"email": "analyst@standardbank.co.za", "name": "Karen", "surname": "Naidoo"},
        ],
        "years": {
            "2021": {"Revenue": 88_000_000, "Profit": 12_800_000, "Assets": 850_000_000, "Liabilities": 700_000_000, "Equity": 150_000_000},
            "2022": {"Revenue": 95_000_000, "Profit": 14_500_000, "Assets": 890_000_000, "Liabilities": 720_000_000, "Equity": 170_000_000},
            "2023": {"Revenue": 102_000_000, "Profit": 16_200_000, "Assets": 920_000_000, "Liabilities": 735_000_000, "Equity": 185_000_000},
            "2024": {"Revenue": 108_000_000, "Profit": 17_800_000, "Assets": 945_000_000, "Liabilities": 740_000_000, "Equity": 205_000_000},
        },
        "extra_reports": 2,
        "failed_reports": 0,
    },
    {
        "company_name": "Shoprite Holdings",
        "registration_number": "SHP-1979-001",
        "website": "https://www.shoprite.co.za",
        "industry": "Retail",
        "jse_code": "SHP",
        "sector": "Food & Drug Retailers",
        "listing_date": date(1986, 11, 17),
        "market_cap": 145_000_000_000,
        "subscription_status": SubscriptionStatus.suspended,
        "admin": {"email": "admin@shoprite.co.za", "name": "Chris", "surname": "Pretorius"},
        "employees": [
            {"email": "store.ops@shoprite.co.za", "name": "Fatima", "surname": "Hassan"},
        ],
        "years": {
            "2021": {"Revenue": 198_000_000, "Profit": 7_800_000, "Assets": 175_000_000, "Liabilities": 115_000_000, "Equity": 60_000_000},
            "2022": {"Revenue": 210_000_000, "Profit": 8_500_000, "Assets": 185_000_000, "Liabilities": 120_000_000, "Equity": 65_000_000},
            "2023": {"Revenue": 225_000_000, "Profit": 9_200_000, "Assets": 192_000_000, "Liabilities": 125_000_000, "Equity": 67_000_000},
            "2024": {"Revenue": 238_000_000, "Profit": 10_100_000, "Assets": 200_000_000, "Liabilities": 128_000_000, "Equity": 72_000_000},
        },
        "extra_reports": 0,
        "failed_reports": 1,
    },
    {
        "company_name": "MTN Group",
        "registration_number": "MTN-1994-001",
        "website": "https://www.mtn.com",
        "industry": "Telecommunications",
        "jse_code": "MTN",
        "sector": "Mobile Telecommunications",
        "listing_date": date(1995, 11, 27),
        "market_cap": 210_000_000_000,
        "subscription_status": SubscriptionStatus.active,
        "admin": {"email": "admin@mtn.co.za", "name": "Lebo", "surname": "Mabaso"},
        "employees": [
            {"email": "network@mtn.co.za", "name": "James", "surname": "Pillay"},
            {"email": "finance@mtn.co.za", "name": "Aisha", "surname": "Patel"},
        ],
        "years": {
            "2021": {"Revenue": 175_000_000, "Profit": 16_000_000, "Assets": 310_000_000, "Liabilities": 180_000_000, "Equity": 130_000_000},
            "2022": {"Revenue": 188_000_000, "Profit": 17_500_000, "Assets": 330_000_000, "Liabilities": 190_000_000, "Equity": 140_000_000},
            "2023": {"Revenue": 201_000_000, "Profit": 19_200_000, "Assets": 355_000_000, "Liabilities": 200_000_000, "Equity": 155_000_000},
            "2024": {"Revenue": 215_000_000, "Profit": 21_000_000, "Assets": 375_000_000, "Liabilities": 205_000_000, "Equity": 170_000_000},
        },
        "extra_reports": 1,
        "failed_reports": 0,
    },
    {
        "company_name": "Anglo American Platinum",
        "registration_number": "AMS-1946-001",
        "website": "https://www.angloamericanplatinum.com",
        "industry": "Mining",
        "jse_code": "AMS",
        "sector": "Platinum & Precious Metals",
        "listing_date": date(1979, 5, 3),
        "market_cap": 185_000_000_000,
        "subscription_status": SubscriptionStatus.trial,
        "admin": {"email": "admin@angloplat.co.za", "name": "Riaan", "surname": "Steyn"},
        "employees": [
            {"email": "ops@angloplat.co.za", "name": "Bongani", "surname": "Nkosi"},
        ],
        "years": {
            "2021": {"Revenue": 140_000_000, "Profit": 28_000_000, "Assets": 250_000_000, "Liabilities": 70_000_000, "Equity": 180_000_000},
            "2022": {"Revenue": 125_000_000, "Profit": 18_000_000, "Assets": 240_000_000, "Liabilities": 75_000_000, "Equity": 165_000_000},
            "2023": {"Revenue": 110_000_000, "Profit": 9_500_000, "Assets": 230_000_000, "Liabilities": 80_000_000, "Equity": 150_000_000},
            "2024": {"Revenue": 118_000_000, "Profit": 12_200_000, "Assets": 235_000_000, "Liabilities": 78_000_000, "Equity": 157_000_000},
        },
        "extra_reports": 1,
        "failed_reports": 0,
    },
    {
        "company_name": "Discovery Limited",
        "registration_number": "DSY-1992-001",
        "website": "https://www.discovery.co.za",
        "industry": "Financial Services",
        "jse_code": "DSY",
        "sector": "Life Insurance & Healthcare",
        "listing_date": date(1999, 10, 21),
        "market_cap": 92_000_000_000,
        "subscription_status": SubscriptionStatus.active,
        "admin": {"email": "admin@discovery.co.za", "name": "Priya", "surname": "Govender"},
        "employees": [
            {"email": "actuarial@discovery.co.za", "name": "Michael", "surname": "Cohen"},
            {"email": "compliance@discovery.co.za", "name": "Thandi", "surname": "Radebe"},
        ],
        "years": {
            "2021": {"Revenue": 72_000_000, "Profit": 5_200_000, "Assets": 210_000_000, "Liabilities": 160_000_000, "Equity": 50_000_000},
            "2022": {"Revenue": 78_000_000, "Profit": 5_800_000, "Assets": 225_000_000, "Liabilities": 168_000_000, "Equity": 57_000_000},
            "2023": {"Revenue": 84_000_000, "Profit": 6_400_000, "Assets": 240_000_000, "Liabilities": 175_000_000, "Equity": 65_000_000},
            "2024": {"Revenue": 91_000_000, "Profit": 7_100_000, "Assets": 255_000_000, "Liabilities": 180_000_000, "Equity": 75_000_000},
        },
        "extra_reports": 1,
        "failed_reports": 0,
    },
    {
        "company_name": "Woolworths Holdings",
        "registration_number": "WHL-1929-001",
        "website": "https://www.woolworthsholdings.co.za",
        "industry": "Retail",
        "jse_code": "WHL",
        "sector": "General Retailers",
        "listing_date": date(1997, 6, 18),
        "market_cap": 58_000_000_000,
        "subscription_status": SubscriptionStatus.inactive,
        "admin": {"email": "admin@woolworths.co.za", "name": "Helen", "surname": "Kruger"},
        "employees": [
            {"email": "merch@woolworths.co.za", "name": "Sibusiso", "surname": "Nkuna"},
        ],
        "years": {
            "2021": {"Revenue": 72_000_000, "Profit": 3_100_000, "Assets": 55_000_000, "Liabilities": 32_000_000, "Equity": 23_000_000},
            "2022": {"Revenue": 76_000_000, "Profit": 3_400_000, "Assets": 58_000_000, "Liabilities": 33_000_000, "Equity": 25_000_000},
            "2023": {"Revenue": 79_000_000, "Profit": 3_700_000, "Assets": 60_000_000, "Liabilities": 34_000_000, "Equity": 26_000_000},
            "2024": {"Revenue": 83_000_000, "Profit": 4_000_000, "Assets": 63_000_000, "Liabilities": 35_000_000, "Equity": 28_000_000},
        },
        "extra_reports": 0,
        "failed_reports": 1,
    },
    {
        "company_name": "Bidvest Group",
        "registration_number": "BVT-1988-001",
        "website": "https://www.bidvest.co.za",
        "industry": "Industrials",
        "jse_code": "BVT",
        "sector": "Industrial Conglomerates",
        "listing_date": date(1990, 9, 17),
        "market_cap": 78_000_000_000,
        "subscription_status": SubscriptionStatus.active,
        "admin": {"email": "admin@bidvest.co.za", "name": "Gerrie", "surname": "Fourie"},
        "employees": [
            {"email": "ops@bidvest.co.za", "name": "Naledi", "surname": "Molefe"},
            {"email": "audit@bidvest.co.za", "name": "Pieter", "surname": "van Zyl"},
        ],
        "years": {
            "2021": {"Revenue": 95_000_000, "Profit": 6_800_000, "Assets": 70_000_000, "Liabilities": 38_000_000, "Equity": 32_000_000},
            "2022": {"Revenue": 102_000_000, "Profit": 7_400_000, "Assets": 74_000_000, "Liabilities": 40_000_000, "Equity": 34_000_000},
            "2023": {"Revenue": 110_000_000, "Profit": 8_100_000, "Assets": 78_000_000, "Liabilities": 41_000_000, "Equity": 37_000_000},
            "2024": {"Revenue": 118_000_000, "Profit": 8_900_000, "Assets": 82_000_000, "Liabilities": 42_000_000, "Equity": 40_000_000},
        },
        "extra_reports": 1,
        "failed_reports": 0,
    },
]

AUDIT_ACTIONS = [
    ("login", "User"),
    ("create", "Company"),
    ("create", "AnnualReport"),
    ("extract", "AnnualReport"),
    ("update", "Company"),
    ("update", "User"),
    ("create", "AnalyticsResult"),
    ("login", "User"),
    ("extract", "ExtractedFinancial"),
    ("update", "GovernanceNarrative"),
    ("delete", "ScheduledReport"),
    ("login", "User"),
    ("upload_report", "AnnualReport"),
    ("run_analytics", "Company"),
    ("invite", "User"),
    ("retry_extraction", "AnnualReport"),
]


def _create_seed_pdf(full_path: str, company_name: str, years: dict | None = None) -> None:
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    c = canvas.Canvas(full_path, pagesize=letter)
    _, height = letter
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, f"{company_name} - Integrated Annual Report 2024")
    y -= 30
    c.setFont("Helvetica", 11)
    for category, content, _ in GOVERNANCE_TEMPLATES:
        c.drawString(50, y, f"{category}: {content[:120]}")
        y -= 18
        if y < 80:
            c.showPage()
            y = height - 50
    if years:
        y -= 10
        for year, metrics in sorted(years.items()):
            c.drawString(50, y, f"Financial Year {year}")
            y -= 18
            for metric_name, value in metrics.items():
                c.drawString(50, y, f"{metric_name}: {value:,.0f}")
                y -= 16
                if y < 80:
                    c.showPage()
                    y = height - 50
    c.save()


def init_db():
    Base.metadata.create_all(bind=engine)


def clear_all(db):
    db.query(EmailVerification).delete()
    db.query(PasswordResetToken).delete()
    db.query(Notification).delete()
    db.query(BackgroundJob).delete()
    db.query(ScheduledReport).delete()
    db.query(AuditLog).delete()
    db.query(AnalyticsResult).delete()
    db.query(ExtractedFinancial).delete()
    db.query(GovernanceNarrative).delete()
    db.query(AnnualReport).delete()
    db.query(User).delete()
    db.query(RegistrationPin).delete()
    db.query(Company).delete()
    db.commit()


def ensure_platform_owner(db):
    settings = get_settings()
    existing = db.query(User).filter(User.email == settings.platform_owner_email).first()
    if existing:
        return existing
    user = User(
        email=settings.platform_owner_email,
        password_hash=hash_password(settings.platform_owner_password),
        name="Platform",
        surname="Owner",
        role=UserRole.platform_owner,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"[SEED] Platform owner: {settings.platform_owner_email}")
    return user


def _add_financials(db, report_id: int, years: dict):
    for year, metrics in years.items():
        for metric_name, value in metrics.items():
            db.add(
                ExtractedFinancial(
                    report_id=report_id,
                    financial_year=year,
                    metric_name=metric_name,
                    metric_value=float(value),
                    category="Financial Statement",
                )
            )


def _add_governance(db, report_id: int, confidence_nudge: float = 0.0):
    for category, content, confidence in GOVERNANCE_TEMPLATES:
        score = min(0.99, max(0.55, confidence + confidence_nudge))
        db.add(
            GovernanceNarrative(
                report_id=report_id,
                category=category,
                content=content,
                confidence_score=score,
            )
        )


def seed_companies(db, owner: User):
    password_hash = hash_password(DEFAULT_PASSWORD)
    created_users: list[User] = [owner]
    company_ids: list[int] = []
    report_ids_by_company: dict[int, list[int]] = {}

    for spec in COMPANY_SEED:
        company = Company(
            company_name=spec["company_name"],
            registration_number=spec["registration_number"],
            website=spec["website"],
            industry=spec["industry"],
            jse_code=spec.get("jse_code"),
            sector=spec.get("sector"),
            listing_date=spec.get("listing_date"),
            market_cap=spec.get("market_cap"),
            subscription_status=spec["subscription_status"],
        )
        db.add(company)
        db.flush()

        company_ids.append(company.id)
        report_ids_by_company[company.id] = []
        print(f"[SEED] Company: {company.company_name} ({spec.get('jse_code', 'n/a')})")

        admin_data = spec["admin"]
        admin = User(
            email=admin_data["email"],
            password_hash=password_hash,
            name=admin_data["name"],
            surname=admin_data["surname"],
            role=UserRole.company_admin,
            company_id=company.id,
            is_active=True,
            phone_number="+27 11 555 0100",
            gender="unspecified",
        )
        db.add(admin)
        created_users.append(admin)

        for emp in spec["employees"]:
            employee = User(
                email=emp["email"],
                password_hash=password_hash,
                name=emp["name"],
                surname=emp["surname"],
                role=UserRole.employee,
                company_id=company.id,
                is_active=True,
            )
            db.add(employee)
            created_users.append(employee)

        db.flush()

        # One complete report per year (multi-year history)
        years = spec["years"]
        year_keys = sorted(years.keys())
        for year in year_keys:
            year_slice = {year: years[year]}
            seed_rel = f"seed/{company.registration_number}_annual_{year}.pdf"
            seed_full = os.path.join(get_settings().upload_dir, seed_rel)
            _create_seed_pdf(seed_full, company.company_name, year_slice)

            report = AnnualReport(
                company_id=company.id,
                file_path=seed_rel,
                status=ReportStatus.complete,
            )
            db.add(report)
            db.flush()
            report_ids_by_company[company.id].append(report.id)

            # Put full multi-year metrics on the latest report; single year on older ones
            if year == year_keys[-1]:
                _add_financials(db, report.id, years)
                _add_governance(db, report.id)
            else:
                _add_financials(db, report.id, year_slice)
                _add_governance(db, report.id, confidence_nudge=-0.05)

        # Pending / processing extras
        for i in range(spec.get("extra_reports", 0)):
            interim_rel = f"seed/{company.registration_number}_interim_{i + 1}.pdf"
            interim_full = os.path.join(get_settings().upload_dir, interim_rel)
            _create_seed_pdf(interim_full, company.company_name)
            pending = AnnualReport(
                company_id=company.id,
                file_path=interim_rel,
                status=ReportStatus.pending if i % 2 == 0 else ReportStatus.processing,
            )
            db.add(pending)
            db.flush()
            report_ids_by_company[company.id].append(pending.id)

        # Failed reports (demo extraction failures)
        for i in range(spec.get("failed_reports", 0)):
            failed_rel = f"seed/{company.registration_number}_failed_{i + 1}.pdf"
            failed_full = os.path.join(get_settings().upload_dir, failed_rel)
            _create_seed_pdf(failed_full, company.company_name)
            failed = AnnualReport(
                company_id=company.id,
                file_path=failed_rel,
                status=ReportStatus.failed,
            )
            db.add(failed)
            db.flush()
            report_ids_by_company[company.id].append(failed.id)

        db.add(
            ScheduledReport(
                company_id=company.id,
                user_id=admin.id,
                report_type="analytics_pdf",
                frequency="monthly",
                is_active=spec["subscription_status"] in (SubscriptionStatus.active, SubscriptionStatus.trial),
                last_sent_at=datetime.now(timezone.utc) - timedelta(days=12) if spec["subscription_status"] == SubscriptionStatus.active else None,
            )
        )

    db.commit()
    return created_users, company_ids, report_ids_by_company


def seed_audit_logs(db, users: list[User]):
    now = datetime.now(timezone.utc)
    logs = []
    for i, (action, entity) in enumerate(AUDIT_ACTIONS * 3):
        user = users[i % len(users)]
        logs.append(
            AuditLog(
                user_id=user.id,
                action=action,
                entity=f"{entity}:{1000 + i}",
                ip_address=f"192.168.1.{10 + (i % 40)}",
                timestamp=now - timedelta(hours=i * 2, minutes=i * 5),
            )
        )
    db.add_all(logs)
    db.commit()
    print(f"[SEED] Audit logs: {len(logs)}")


def seed_notifications(db, users: list[User], company_ids: list[int]):
    """Light product notifications so dashboards are not empty."""
    now = datetime.now(timezone.utc)
    samples = [
        (NotificationType.extraction_complete, "Extraction complete", "Annual report extraction finished successfully."),
        (NotificationType.analytics_updated, "Analytics updated", "Company scores and trends were recalculated."),
        (NotificationType.report_uploaded, "New report uploaded", "A PDF annual report was uploaded and queued."),
        (NotificationType.risk_changed, "Risk classification updated", "Risk level changed based on latest financials."),
        (NotificationType.system_alert, "Welcome to JSE Analytics", "Your demo workspace is ready."),
    ]
    count = 0
    company_users = [u for u in users if u.company_id]
    for i, user in enumerate(company_users):
        ntype, title, message = samples[i % len(samples)]
        db.add(
            Notification(
                user_id=user.id,
                company_id=user.company_id,
                notification_type=ntype,
                title=title,
                message=message,
                entity_ref=f"company:{user.company_id}",
                is_read=(i % 3 == 0),
                created_at=now - timedelta(hours=i * 4),
            )
        )
        count += 1
    # Platform owner inbox sample
    owners = [u for u in users if u.role == UserRole.platform_owner]
    for owner in owners:
        db.add(
            Notification(
                user_id=owner.id,
                company_id=None,
                notification_type=NotificationType.system_alert,
                title="Platform health OK",
                message="Seed completed. Demo companies, reports, and analytics are available.",
                entity_ref="system:seed",
                is_read=False,
            )
        )
        count += 1
    db.commit()
    print(f"[SEED] Notifications: {count}")


def seed_background_jobs(db, report_ids_by_company: dict[int, list[int]]):
    """Sample completed/pending jobs so job queue UI has data."""
    import json

    now = datetime.now(timezone.utc)
    count = 0
    for company_id, report_ids in report_ids_by_company.items():
        if not report_ids:
            continue
        rid = report_ids[0]
        db.add(
            BackgroundJob(
                job_type="extraction",
                payload_json=json.dumps({"report_id": rid, "report_year": "2024"}),
                status=JobStatus.complete,
                attempts=1,
                started_at=now - timedelta(hours=5),
                completed_at=now - timedelta(hours=4, minutes=50),
            )
        )
        count += 1
        if len(report_ids) > 1:
            db.add(
                BackgroundJob(
                    job_type="extraction",
                    payload_json=json.dumps({"report_id": report_ids[-1]}),
                    status=JobStatus.pending,
                    attempts=0,
                )
            )
            count += 1
    db.commit()
    print(f"[SEED] Background jobs: {count}")


def seed_analytics(company_ids: list[int]):
    for company_id in company_ids:
        run_company_analytics(company_id)
    print(f"[SEED] Analytics computed for {len(company_ids)} companies")


def ensure_seed_pdf_files(db):
    """Fix legacy paths and create missing demo PDF files."""
    settings = get_settings()
    for report in db.query(AnnualReport).all():
        if report.file_path.startswith("uploads/seed/"):
            report.file_path = report.file_path.replace("uploads/seed/", "seed/", 1)
        full_path = os.path.join(settings.upload_dir, report.file_path)
        if os.path.exists(full_path):
            continue
        company = db.query(Company).filter(Company.id == report.company_id).first()
        if not company:
            continue
        spec = next((c for c in COMPANY_SEED if c["registration_number"] == company.registration_number), None)
        years = spec["years"] if spec and "annual" in report.file_path else None
        _create_seed_pdf(full_path, company.company_name, years)
        print(f"[SEED] Created PDF: {report.file_path}")
    db.commit()


def seed(reset: bool = False, owner_only: bool = False):
    init_db()
    db = SessionLocal()
    try:
        if owner_only:
            ensure_platform_owner(db)
            print("[SEED] Platform owner ensured.")
            return

        if db.query(Company).count() > 0 and not reset:
            ensure_platform_owner(db)
            ensure_seed_pdf_files(db)
            print("[SEED] Demo data already exists. Run with --reset to wipe and reseed.")
            return

        if reset:
            print("[SEED] Clearing existing data...")
            clear_all(db)

        owner = ensure_platform_owner(db)
        users, company_ids, report_ids_by_company = seed_companies(db, owner)
        seed_audit_logs(db, users)
        seed_notifications(db, users, company_ids)
        seed_background_jobs(db, report_ids_by_company)
        seed_analytics(company_ids)

        settings = get_settings()
        print("\n[SEED] Database seeded successfully.\n")
        print(f"  Companies: {len(company_ids)}")
        print(f"  Users:     {len(users)}")
        print(f"  Reports:   {db.query(AnnualReport).count()}")
        print(f"  Financial: {db.query(ExtractedFinancial).count()}")
        print(f"  Governance:{db.query(GovernanceNarrative).count()}")
        print(f"  Analytics: {db.query(AnalyticsResult).count()}")
        print("\nLogin credentials:")
        print(f"  Platform owner:  {settings.platform_owner_email} / {settings.platform_owner_password}")
        print(f"  Company admins:  *@*.co.za / {DEFAULT_PASSWORD}")
        print(f"  Employees:       *@*.co.za / {DEFAULT_PASSWORD}")
        print("\nExample accounts:")
        print(f"  Company admin:   admin@bluemachines.co.za / {DEFAULT_PASSWORD}")
        print(f"  Employee:        john.doe@bluemachines.co.za / {DEFAULT_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed JSE Analytics database")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all data and reseed from scratch",
    )
    parser.add_argument(
        "--owner-only",
        action="store_true",
        help="Ensure platform owner exists without demo data (production)",
    )
    args = parser.parse_args()
    seed(reset=args.reset, owner_only=args.owner_only)
