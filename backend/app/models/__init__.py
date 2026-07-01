import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UserRole(str, enum.Enum):
    platform_owner = "platform_owner"
    company_admin = "company_admin"
    employee = "employee"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    trial = "trial"
    suspended = "suspended"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class RegistrationType(str, enum.Enum):
    admin = "admin"
    company = "company"
    employee = "employee"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.trial
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship("User", back_populates="company")
    annual_reports: Mapped[list["AnnualReport"]] = relationship("AnnualReport", back_populates="company")
    analytics_results: Mapped[list["AnalyticsResult"]] = relationship("AnalyticsResult", back_populates="company")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("companies.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    surname: Mapped[str] = mapped_column(String(100), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    profile_photo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    company: Mapped["Company | None"] = relationship("Company", back_populates="users")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")


class AnnualReport(Base):
    __tablename__ = "annual_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.pending)

    company: Mapped["Company"] = relationship("Company", back_populates="annual_reports")
    extracted_financials: Mapped[list["ExtractedFinancial"]] = relationship(
        "ExtractedFinancial", back_populates="report"
    )
    governance_narratives: Mapped[list["GovernanceNarrative"]] = relationship(
        "GovernanceNarrative", back_populates="report"
    )


class ExtractedFinancial(Base):
    __tablename__ = "extracted_financials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(Integer, ForeignKey("annual_reports.id"), nullable=False)
    financial_year: Mapped[str] = mapped_column(String(20), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    report: Mapped["AnnualReport"] = relationship("AnnualReport", back_populates="extracted_financials")


class GovernanceNarrative(Base):
    __tablename__ = "governance_narratives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(Integer, ForeignKey("annual_reports.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)

    report: Mapped["AnnualReport"] = relationship("AnnualReport", back_populates="governance_narratives")


class AnalyticsResult(Base):
    __tablename__ = "analytics_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(100), nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    company: Mapped["Company"] = relationship("Company", back_populates="analytics_results")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    entity: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs")


class RegistrationPin(Base):
    __tablename__ = "registration_pins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    registration_type: Mapped[RegistrationType] = mapped_column(Enum(RegistrationType), nullable=False)
    user_data_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScheduledReport(Base):
    __tablename__ = "scheduled_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    frequency: Mapped[str] = mapped_column(String(50), default="monthly")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
