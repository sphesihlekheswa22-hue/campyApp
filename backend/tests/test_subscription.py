import pytest
from fastapi import HTTPException

from app.models import Company, SubscriptionStatus
from app.services.subscription_service import assert_company_active, ALLOWED_STATUSES


def test_allowed_subscription_statuses():
    assert SubscriptionStatus.active in ALLOWED_STATUSES
    assert SubscriptionStatus.trial in ALLOWED_STATUSES
    assert SubscriptionStatus.suspended not in ALLOWED_STATUSES
    assert SubscriptionStatus.inactive not in ALLOWED_STATUSES


def test_assert_company_active_allows_trial():
    company = Company(
        company_name="Test Co",
        registration_number="TEST/001",
        subscription_status=SubscriptionStatus.trial,
    )
    assert_company_active(company)


def test_assert_company_active_blocks_suspended():
    company = Company(
        company_name="Test Co",
        registration_number="TEST/002",
        subscription_status=SubscriptionStatus.suspended,
    )
    with pytest.raises(HTTPException) as exc:
        assert_company_active(company)
    assert exc.value.status_code == 403


def test_assert_company_active_blocks_missing_company():
    with pytest.raises(HTTPException) as exc:
        assert_company_active(None)
    assert exc.value.status_code == 403
