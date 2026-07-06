"""Seed database with platform owner, demo companies, reports, analytics, and audit logs."""
import argparse
import os
from datetime import datetime, timedelta, timezone

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
    Company,
    ExtractedFinancial,
    GovernanceNarrative,
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

COMPANY_SEED = [
    {
        "company_name": "Blue Machines Ltd",
        "registration_number": "BM-2020-001",
        "website": "https://bluemachines.co.za",
        "industry": "Technology",
        "subscription_status": SubscriptionStatus.active,
        "admin": {"email": "admin@bluemachines.co.za", "name": "Sarah", "surname": "Ndlovu"},
        "employees": [
            {"email": "john.doe@bluemachines.co.za", "name": "John", "surname": "Doe"},
            {"email": "jane.smith@bluemachines.co.za", "name": "Jane", "surname": "Smith"},
            {"email": "peter.mokoena@bluemachines.co.za", "name": "Peter", "surname": "Mokoena"},
        ],
        "years": {
            "2022": {"Revenue": 45_000_000, "Profit": 3_200_000, "Assets": 120_000_000, "Liabilities": 45_000_000, "Equity": 75_000_000},
            "2023": {"Revenue": 52_000_000, "Profit": 4_100_000, "Assets": 135_000_000, "Liabilities": 48_000_000, "Equity": 87_000_000},
            "2024": {"Revenue": 61_000_000, "Profit": 5_400_000, "Assets": 148_000_000, "Liabilities": 50_000_000, "Equity": 98_000_000},
        },
        "extra_reports": 1,
    },
    {
        "company_name": "Naspers Limited",
        "registration_number": "NPN-1915-001",
        "website": "https://www.naspers.com",
        "industry": "Media",
        "subscription_status": SubscriptionStatus.active,
        "admin": {"email": "admin@naspers.co.za", "name": "William", "surname": "Joubert"},
        "employees": [
            {"email": "analyst@naspers.co.za", "name": "Lindiwe", "surname": "Khumalo"},
        ],
        "years": {
            "2022": {"Revenue": 180_000_000, "Profit": 22_000_000, "Assets": 420_000_000, "Liabilities": 95_000_000, "Equity": 325_000_000},
            "2023": {"Revenue": 195_000_000, "Profit": 24_500_000, "Assets": 445_000_000, "Liabilities": 98_000_000, "Equity": 357_000_000},
            "2024": {"Revenue": 210_000_000, "Profit": 27_800_000, "Assets": 470_000_000, "Liabilities": 100_000_000, "Equity": 370_000_000},
        },
        "extra_reports": 0,
    },
    {
        "company_name": "Sasol Limited",
        "registration_number": "SOL-1950-001",
        "website": "https://www.sasol.com",
        "industry": "Energy",
        "subscription_status": SubscriptionStatus.trial,
        "admin": {"email": "admin@sasol.co.za", "name": "Thabo", "surname": "Molefe"},
        "employees": [
            {"email": "engineer@sasol.co.za", "name": "David", "surname": "Botha"},
        ],
        "years": {
            "2022": {"Revenue": 320_000_000, "Profit": 18_000_000, "Assets": 580_000_000, "Liabilities": 310_000_000, "Equity": 270_000_000},
            "2023": {"Revenue": 295_000_000, "Profit": 12_500_000, "Assets": 560_000_000, "Liabilities": 320_000_000, "Equity": 240_000_000},
            "2024": {"Revenue": 310_000_000, "Profit": 15_200_000, "Assets": 575_000_000, "Liabilities": 315_000_000, "Equity": 260_000_000},
        },
        "extra_reports": 0,
    },
    {
        "company_name": "Standard Bank Group",
        "registration_number": "SBK-1862-001",
        "website": "https://www.standardbank.co.za",
        "industry": "Financial Services",
        "subscription_status": SubscriptionStatus.active,
        "admin": {"email": "admin@standardbank.co.za", "name": "Michelle", "surname": "van Wyk"},
        "employees": [
            {"email": "risk@standardbank.co.za", "name": "Sipho", "surname": "Dlamini"},
            {"email": "compliance@standardbank.co.za", "name": "Nomsa", "surname": "Zulu"},
        ],
        "years": {
            "2022": {"Revenue": 95_000_000, "Profit": 14_500_000, "Assets": 890_000_000, "Liabilities": 720_000_000, "Equity": 170_000_000},
            "2023": {"Revenue": 102_000_000, "Profit": 16_200_000, "Assets": 920_000_000, "Liabilities": 735_000_000, "Equity": 185_000_000},
            "2024": {"Revenue": 108_000_000, "Profit": 17_800_000, "Assets": 945_000_000, "Liabilities": 740_000_000, "Equity": 195_000_000},
        },
        "extra_reports": 1,
    },
    {
        "company_name": "Shoprite Holdings",
        "registration_number": "SHP-1979-001",
        "website": "https://www.shoprite.co.za",
        "industry": "Retail",
        "subscription_status": SubscriptionStatus.suspended,
        "admin": {"email": "admin@shoprite.co.za", "name": "Chris", "surname": "Pretorius"},
        "employees": [
            {"email": "store.ops@shoprite.co.za", "name": "Fatima", "surname": "Hassan"},
        ],
        "years": {
            "2022": {"Revenue": 210_000_000, "Profit": 8_500_000, "Assets": 185_000_000, "Liabilities": 120_000_000, "Equity": 65_000_000},
            "2023": {"Revenue": 225_000_000, "Profit": 9_200_000, "Assets": 192_000_000, "Liabilities": 125_000_000, "Equity": 67_000_000},
            "2024": {"Revenue": 238_000_000, "Profit": 10_100_000, "Assets": 200_000_000, "Liabilities": 128_000_000, "Equity": 72_000_000},
        },
        "extra_reports": 0,
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


def _add_governance(db, report_id: int):
    for category, content, confidence in GOVERNANCE_TEMPLATES:
        db.add(
            GovernanceNarrative(
                report_id=report_id,
                category=category,
                content=content,
                confidence_score=confidence,
            )
        )


def seed_companies(db, owner: User):
    password_hash = hash_password(DEFAULT_PASSWORD)
    created_users: list[User] = [owner]
    company_ids: list[int] = []

    for spec in COMPANY_SEED:
        company = Company(
            company_name=spec["company_name"],
            registration_number=spec["registration_number"],
            website=spec["website"],
            industry=spec["industry"],
            subscription_status=spec["subscription_status"],
        )
        db.add(company)
        db.flush()

        company_ids.append(company.id)
        print(f"[SEED] Company: {company.company_name}")

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

        seed_rel = f"seed/{company.registration_number}_annual_2024.pdf"
        seed_full = os.path.join(get_settings().upload_dir, seed_rel)
        _create_seed_pdf(seed_full, company.company_name, spec["years"])

        main_report = AnnualReport(
            company_id=company.id,
            file_path=seed_rel,
            status=ReportStatus.complete,
        )
        db.add(main_report)
        db.flush()

        _add_financials(db, main_report.id, spec["years"])
        _add_governance(db, main_report.id)

        for i in range(spec.get("extra_reports", 0)):
            interim_rel = f"seed/{company.registration_number}_interim_{i + 1}.pdf"
            interim_full = os.path.join(get_settings().upload_dir, interim_rel)
            _create_seed_pdf(interim_full, company.company_name)
            pending = AnnualReport(
                company_id=company.id,
                file_path=interim_rel,
                status=ReportStatus.pending if i == 0 else ReportStatus.processing,
            )
            db.add(pending)

        db.add(
            ScheduledReport(
                company_id=company.id,
                user_id=admin.id,
                report_type="analytics_pdf",
                frequency="monthly",
                is_active=True,
            )
        )

    db.commit()
    return created_users, company_ids


def seed_audit_logs(db, users: list[User]):
    now = datetime.now(timezone.utc)
    logs = []
    for i, (action, entity) in enumerate(AUDIT_ACTIONS):
        user = users[i % len(users)]
        logs.append(
            AuditLog(
                user_id=user.id,
                action=action,
                entity=entity,
                ip_address=f"192.168.1.{10 + i}",
                timestamp=now - timedelta(hours=i * 3, minutes=i * 7),
            )
        )
    db.add_all(logs)
    db.commit()
    print(f"[SEED] Audit logs: {len(logs)}")


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


def seed(reset: bool = False):
    init_db()
    db = SessionLocal()
    try:
        if db.query(Company).count() > 0 and not reset:
            ensure_platform_owner(db)
            ensure_seed_pdf_files(db)
            print("[SEED] Demo data already exists. Run with --reset to wipe and reseed.")
            return

        if reset:
            print("[SEED] Clearing existing data...")
            clear_all(db)

        owner = ensure_platform_owner(db)
        users, company_ids = seed_companies(db, owner)
        seed_audit_logs(db, users)
        seed_analytics(company_ids)

        settings = get_settings()
        print("\n[SEED] Database seeded successfully.\n")
        print("Login credentials:")
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
    args = parser.parse_args()
    seed(reset=args.reset)
