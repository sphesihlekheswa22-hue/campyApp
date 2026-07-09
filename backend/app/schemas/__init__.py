from datetime import date, datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models import NotificationType, ReportStatus, SubscriptionStatus, UserRole

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    role: str
    user_id: int
    must_change_password: bool = False

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AdminRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str
    surname: str
    phone_number: Optional[str] = None
    gender: Optional[str] = None


class CompanyRegisterRequest(BaseModel):
    company_name: str
    registration_number: str
    website: Optional[str] = None
    industry: Optional[str] = None
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)
    admin_name: str
    admin_surname: str


class EmployeeRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str
    surname: str
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    company_id: int


class ConfirmPinRequest(BaseModel):
    registration_id: str
    pin: str = Field(min_length=6, max_length=6)


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class RegistrationResponse(BaseModel):
    registration_id: str
    message: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    surname: str
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    profile_photo: Optional[str] = None
    role: UserRole
    company_id: Optional[int] = None
    is_active: bool
    must_change_password: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: Optional[str] = Field(default=None, min_length=8)
    name: str
    surname: str
    role: UserRole
    company_id: Optional[int] = None
    phone_number: Optional[str] = None
    send_invite_email: bool = True


class CompanyResponse(BaseModel):
    id: int
    company_name: str
    registration_number: str
    website: Optional[str] = None
    logo: Optional[str] = None
    industry: Optional[str] = None
    jse_code: Optional[str] = None
    sector: Optional[str] = None
    listing_date: Optional[date] = None
    market_cap: Optional[float] = None
    subscription_status: SubscriptionStatus
    created_at: datetime

    class Config:
        from_attributes = True


class CompanyListResponse(CompanyResponse):
    report_count: int = 0


class CompanyCreateRequest(BaseModel):
    company_name: str
    registration_number: str
    website: Optional[str] = None
    industry: Optional[str] = None
    jse_code: Optional[str] = None
    sector: Optional[str] = None
    listing_date: Optional[date] = None
    market_cap: Optional[float] = None
    subscription_status: SubscriptionStatus = SubscriptionStatus.trial
    admin_email: Optional[EmailStr] = None
    admin_password: Optional[str] = Field(default=None, min_length=8)
    admin_name: Optional[str] = None
    admin_surname: Optional[str] = None

    @model_validator(mode="after")
    def validate_admin_fields(self):
        admin_fields = [self.admin_email, self.admin_password, self.admin_name, self.admin_surname]
        if any(admin_fields) and not all(admin_fields):
            raise ValueError("All company admin fields are required when adding an admin")
        return self


class CompanyUpdateRequest(BaseModel):
    company_name: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    jse_code: Optional[str] = None
    sector: Optional[str] = None
    listing_date: Optional[date] = None
    market_cap: Optional[float] = None
    subscription_status: Optional[SubscriptionStatus] = None


class NotificationResponse(BaseModel):
    id: int
    notification_type: NotificationType
    title: str
    message: str
    entity_ref: Optional[str] = None
    company_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduledReportResponse(BaseModel):
    id: int
    company_id: int
    user_id: int
    report_type: str
    frequency: str
    is_active: bool
    last_sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduledReportCreateRequest(BaseModel):
    company_id: int
    report_type: str = "analytics_summary"
    frequency: str = "monthly"


class ComplianceChecklistResponse(BaseModel):
    items: list[dict]
    summary: dict
    category_scores: dict


class ReportResponse(BaseModel):
    id: int
    company_id: int
    file_path: str
    upload_date: datetime
    status: ReportStatus

    class Config:
        from_attributes = True


class FinancialResponse(BaseModel):
    id: int
    report_id: int
    financial_year: str
    metric_name: str
    metric_value: float
    category: str

    class Config:
        from_attributes = True


class GovernanceResponse(BaseModel):
    id: int
    report_id: int
    category: str
    content: str
    confidence_score: float

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    entity: str
    timestamp: datetime
    ip_address: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True


class AnalyticsResultResponse(BaseModel):
    id: int
    company_id: int
    analysis_type: str
    result_json: str
    created_at: datetime

    class Config:
        from_attributes = True


class SystemHealthResponse(BaseModel):
    status: str
    database: str
    total_users: int
    total_companies: int
    total_reports: int
    pending_extractions: int
    failed_extractions: int = 0
    pending_jobs: int = 0
    alerts: list[str] = []


class ReportExtractionSummary(BaseModel):
    report_id: int
    status: ReportStatus
    financial_count: int
    governance_count: int
    financial_year: Optional[str] = None
    extraction_issues: list[str] = []
