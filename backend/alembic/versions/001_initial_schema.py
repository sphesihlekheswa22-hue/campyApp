"""Initial schema

Revision ID: 001
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("registration_number", sa.String(100), nullable=False),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("logo", sa.String(500), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("subscription_status", sa.Enum("active", "inactive", "trial", "suspended", name="subscriptionstatus"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_number"),
    )
    op.create_index("ix_companies_id", "companies", ["id"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("surname", sa.String(100), nullable=False),
        sa.Column("phone_number", sa.String(50), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("profile_photo", sa.String(500), nullable=True),
        sa.Column("role", sa.Enum("platform_owner", "company_admin", "employee", name="userrole"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_id", "users", ["id"])

    op.create_table(
        "annual_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("upload_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("status", sa.Enum("pending", "processing", "complete", "failed", name="reportstatus"), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_annual_reports_id", "annual_reports", ["id"])

    op.create_table(
        "extracted_financials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("financial_year", sa.String(20), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["annual_reports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "governance_narratives",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["report_id"], ["annual_reports.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "analytics_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("analysis_type", sa.String(100), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("entity", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "registration_pins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("pin_hash", sa.String(255), nullable=False),
        sa.Column("registration_id", sa.String(100), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registration_type", sa.Enum("admin", "company", "employee", name="registrationtype"), nullable=False),
        sa.Column("user_data_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_id"),
    )
    op.create_index("ix_registration_pins_email", "registration_pins", ["email"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "email_verifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "scheduled_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("frequency", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("scheduled_reports")
    op.drop_table("email_verifications")
    op.drop_table("password_reset_tokens")
    op.drop_table("registration_pins")
    op.drop_table("audit_logs")
    op.drop_table("analytics_results")
    op.drop_table("governance_narratives")
    op.drop_table("extracted_financials")
    op.drop_table("annual_reports")
    op.drop_table("users")
    op.drop_table("companies")
