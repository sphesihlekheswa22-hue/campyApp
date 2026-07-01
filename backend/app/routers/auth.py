import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database.session import get_db
from app.models import (
    Company,
    EmailVerification,
    PasswordResetToken,
    RegistrationPin,
    RegistrationType,
    SubscriptionStatus,
    User,
    UserRole,
)
from app.schemas import (
    AdminRegisterRequest,
    CompanyRegisterRequest,
    ConfirmPinRequest,
    EmployeeRegisterRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegistrationResponse,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.services.audit_service import log_audit
from app.services.email_service import (
    generate_pin,
    generate_registration_id,
    generate_token,
    hash_token,
    pin_expiry,
    send_password_reset_email,
    send_pin_email,
    send_verification_email,
    token_expiry_hours,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/admin", response_model=RegistrationResponse)
def register_admin(data: AdminRegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    pin = generate_pin()
    reg_id = generate_registration_id()
    user_data = {
        "email": data.email,
        "password": data.password,
        "name": data.name,
        "surname": data.surname,
        "phone_number": data.phone_number,
        "gender": data.gender,
        "role": UserRole.platform_owner.value,
    }
    reg_pin = RegistrationPin(
        email=data.email,
        pin_hash=hash_token(pin),
        registration_id=reg_id,
        expires_at=pin_expiry(),
        registration_type=RegistrationType.admin,
        user_data_json=json.dumps(user_data),
    )
    db.add(reg_pin)
    db.commit()
    send_pin_email(data.email, pin, reg_id)
    return RegistrationResponse(registration_id=reg_id, message="PIN sent to email")


@router.post("/register/company", response_model=RegistrationResponse)
def register_company(data: CompanyRegisterRequest, db: Session = Depends(get_db)):
    if db.query(Company).filter(Company.registration_number == data.registration_number).first():
        raise HTTPException(status_code=400, detail="Company registration number already exists")
    if db.query(User).filter(User.email == data.admin_email).first():
        raise HTTPException(status_code=400, detail="Admin email already registered")

    pin = generate_pin()
    reg_id = generate_registration_id()
    user_data = {
        "company_name": data.company_name,
        "registration_number": data.registration_number,
        "website": data.website,
        "industry": data.industry,
        "admin_email": data.admin_email,
        "admin_password": data.admin_password,
        "admin_name": data.admin_name,
        "admin_surname": data.admin_surname,
    }
    reg_pin = RegistrationPin(
        email=data.admin_email,
        pin_hash=hash_token(pin),
        registration_id=reg_id,
        expires_at=pin_expiry(),
        registration_type=RegistrationType.company,
        user_data_json=json.dumps(user_data),
    )
    db.add(reg_pin)
    db.commit()
    send_pin_email(data.admin_email, pin, reg_id)
    return RegistrationResponse(registration_id=reg_id, message="PIN sent to admin email")


@router.post("/register/employee", response_model=RegistrationResponse)
def register_employee(data: EmployeeRegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    company = db.query(Company).filter(Company.id == data.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        surname=data.surname,
        phone_number=data.phone_number,
        gender=data.gender,
        role=UserRole.employee,
        company_id=data.company_id,
        is_active=False,
    )
    db.add(user)
    db.flush()

    token = generate_token()
    verification = EmailVerification(
        user_id=user.id,
        token_hash=hash_token(token),
    )
    db.add(verification)
    db.commit()
    send_verification_email(data.email, token)
    return RegistrationResponse(registration_id=str(user.id), message="Verification email sent")


@router.post("/confirm-pin")
def confirm_pin(data: ConfirmPinRequest, db: Session = Depends(get_db)):
    reg_pin = db.query(RegistrationPin).filter(
        RegistrationPin.registration_id == data.registration_id
    ).first()
    if not reg_pin:
        raise HTTPException(status_code=400, detail="Invalid registration ID")
    if reg_pin.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="PIN expired")
    if reg_pin.pin_hash != hash_token(data.pin):
        raise HTTPException(status_code=400, detail="Invalid PIN")

    user_data = json.loads(reg_pin.user_data_json)

    if reg_pin.registration_type == RegistrationType.admin:
        user = User(
            email=user_data["email"],
            password_hash=hash_password(user_data["password"]),
            name=user_data["name"],
            surname=user_data["surname"],
            phone_number=user_data.get("phone_number"),
            gender=user_data.get("gender"),
            role=UserRole.platform_owner,
            is_active=True,
        )
        db.add(user)
    elif reg_pin.registration_type == RegistrationType.company:
        company = Company(
            company_name=user_data["company_name"],
            registration_number=user_data["registration_number"],
            website=user_data.get("website"),
            industry=user_data.get("industry"),
            subscription_status=SubscriptionStatus.trial,
        )
        db.add(company)
        db.flush()
        user = User(
            email=user_data["admin_email"],
            password_hash=hash_password(user_data["admin_password"]),
            name=user_data["admin_name"],
            surname=user_data["admin_surname"],
            role=UserRole.company_admin,
            company_id=company.id,
            is_active=True,
        )
        db.add(user)

    db.delete(reg_pin)
    db.commit()
    return {"message": "Account activated successfully"}


@router.post("/verify-email")
def verify_email(data: VerifyEmailRequest, db: Session = Depends(get_db)):
    token_hash = hash_token(data.token)
    verification = db.query(EmailVerification).filter(
        EmailVerification.token_hash == token_hash,
        EmailVerification.verified_at.is_(None),
    ).first()
    if not verification:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    verification.verified_at = datetime.now(timezone.utc)
    user = db.query(User).filter(User.id == verification.user_id).first()
    if user:
        user.is_active = True
    db.commit()
    return {"message": "Email verified successfully"}


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account not activated")

    access = create_access_token(user.id, user.role.value)
    refresh = create_refresh_token(user.id, user.role.value)
    log_audit(db, user.id, "login", f"user:{user.id}", request.client.host if request.client else None)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        role=user.role.value,
        user_id=user.id,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(data: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    return TokenResponse(
        access_token=create_access_token(user.id, user.role.value),
        refresh_token=create_refresh_token(user.id, user.role.value),
        role=user.role.value,
        user_id=user.id,
    )


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        return {"message": "If email exists, reset link sent"}
    token = generate_token()
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=token_expiry_hours(1),
    )
    db.add(reset)
    db.commit()
    send_password_reset_email(data.email, token)
    return {"message": "If email exists, reset link sent"}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = hash_token(data.token)
    reset = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash
    ).first()
    if not reset or reset.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == reset.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(data.new_password)
    db.delete(reset)
    db.commit()
    return {"message": "Password reset successfully"}
