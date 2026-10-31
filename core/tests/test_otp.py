"""Tests for the phone OTP login flow (Bale Gateway)."""

import datetime
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import PhoneOtp

User = get_user_model()

MOCK_BALANCE = {"amount": 150000, "currency": "IRR"}
FIXED_CODE = "123456"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def phone():
    return "09123456789"


@pytest.fixture(autouse=True)
def v2_gateway(monkeypatch):
    """Run the shared OTP-flow tests over the legacy v2 gateway route.

    v3 (Safir send_message, the documented default) is covered separately
    in the ``test_gateway_v3_*`` cases below.
    """

    monkeypatch.setattr(settings, "BALE_OTP_GATEWAY", "v2", raising=False)


@pytest.fixture
def gateway_success():
    """Patch the gateway ``send_otp`` call used inside the OTP service."""

    with patch("accounts.services.otp.gateway_send_otp_v2") as mock_send:
        mock_send.return_value = {
            "phone": "989123456789",
            "balance": MOCK_BALANCE,
        }
        yield mock_send


@pytest.fixture(autouse=True)
def fixed_code(request, monkeypatch):
    """Use a deterministic code so tests can verify without brute force.

    Tagged ``@pytest.mark.natural_code`` tests skip this and exercise the
    real (settings-aware, random) generator instead.
    """

    if request.node.get_closest_marker("natural_code"):
        return

    monkeypatch.setattr(
        "accounts.services.otp._generate_code", lambda: FIXED_CODE
    )


@pytest.fixture(autouse=True)
def disable_drf_throttling(monkeypatch):
    """DRF throttle scopes are bypassed here; the hourly gateway cap is
    covered on the service level in ``test_request_otp_enforces_hourly_limit``.
    """

    monkeypatch.setattr(
        "rest_framework.throttling.ScopedRateThrottle.THROTTLE_RATES",
        {"otp_request": None, "otp_verify": None},
    )


@pytest.mark.django_db
def test_request_otp_stores_hashed_code(api_client, phone, gateway_success):
    url = reverse("otp-request")
    response = api_client.post(url, {"phone": phone}, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["detail"] == "OTP code sent successfully."
    # Gateway wallet balance is deliberately not exposed publicly.
    assert "balance" not in response.data
    assert response.data["expires_in"] == 120

    record = PhoneOtp.objects.get(phone=phone)
    # Only a salted hash is stored, never the raw digits.
    assert FIXED_CODE not in record.code_hash
    assert ":" in record.code_hash
    assert not record.is_expired
    assert record.attempts == 0

    # The gateway client normalizes locally formatted numbers itself.
    sent_phone, sent_otp = gateway_success.call_args[0]
    from accounts.services.bale_otp import normalize_bale_phone

    assert normalize_bale_phone(sent_phone) == "989123456789"
    assert 3 <= len(str(sent_otp)) <= 8


@pytest.mark.django_db
def test_gateway_v3_dispatch_returns_message_id(api_client, phone):
    """Default route (BALE_OTP_GATEWAY=v3) surfaces the Safir message_id."""

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(settings, "BALE_OTP_GATEWAY", "v3", raising=False)
    try:
        with patch(
            "accounts.services.otp.gateway_send_otp_v3",
            return_value={"message_id": "BvQjaR.fIKt7kH.EXTddgYduJ2"},
        ) as mock_v3:
            response = api_client.post(
                reverse("otp-request"), {"phone": phone}, format="json"
            )
    finally:
        monkeypatch.undo()

    assert response.status_code == status.HTTP_200_OK
    assert response.data["detail"] == "OTP code sent successfully."
    assert response.data["message_id"] == "BvQjaR.fIKt7kH.EXTddgYduJ2"
    mock_v3.assert_called_once()


def test_gateway_v3_payload_matches_docs():
    """The send_message payload must match the official sample exactly."""

    from accounts.services.bale_gateway import BaleGatewayService

    service = BaleGatewayService(access_key="test-key", bot_id=123456789)
    payload = service._build_payload("09123456789", "123456")

    assert set(payload) == {"request_id", "bot_id", "phone_number", "message_data"}
    # request_id is a random-generated string (uuid4 here).
    assert isinstance(payload["request_id"], str) and payload["request_id"]
    assert payload["bot_id"] == 123456789 and isinstance(payload["bot_id"], int)
    assert payload["phone_number"] == "989123456789"
    assert payload["message_data"] == {
        "otp_message": {"otp": "123456"},
    }


def test_gateway_v3_sends_documented_request(monkeypatch):
    """HTTP layer uses the documented v3 endpoint, headers and JSON body."""

    from accounts.services import bale_gateway

    captured = {}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"message_id": "BvQjaR.fIKt7kH.EXTddgYduJ2"}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured.update(
            url=url, json=json, headers=headers, timeout=timeout
        )
        return FakeResponse()

    monkeypatch.setattr(bale_gateway.requests, "post", fake_post)

    service = bale_gateway.BaleGatewayService(
        access_key="test-key", bot_id=123456789
    )
    result = service.send_otp("09123456789", 123456)

    assert result == {"message_id": "BvQjaR.fIKt7kH.EXTddgYduJ2"}
    assert captured["url"] == "https://safir.bale.ai/api/v3/send_message"
    assert captured["headers"] == {
        "Content-Type": "application/json",
        "api-access-key": "test-key",
    }
    assert captured["json"]["request_id"]
    assert captured["json"]["bot_id"] == 123456789
    assert captured["json"]["phone_number"] == "989123456789"
    assert captured["json"]["message_data"] == {
        "otp_message": {"otp": "123456"},
    }


def test_gateway_v3_error_mapping(monkeypatch):
    """Documented error statuses map onto clean exceptions."""

    from accounts.services import bale_gateway

    def make_post(status_code):
        class FakeResponse:
            @staticmethod
            def json():
                return {}

        FakeResponse.status_code = status_code
        return lambda url, **kwargs: FakeResponse()

    service = bale_gateway.BaleGatewayService(
        access_key="test-key", bot_id=1
    )

    cases = [
        (
            400,
            bale_gateway.InvalidPhoneNumberError,
            "Invalid destination phone number.",
        ),
        (401, ImproperlyConfigured, None),
        (429, bale_gateway.GatewayRateLimitError, None),
        (500, bale_gateway.GatewayServerError, None),
    ]

    for status_code, expected_error, expected_message in cases:
        monkeypatch.setattr(bale_gateway.requests, "post", make_post(status_code))
        with pytest.raises(expected_error) as excinfo:
            service.send_otp("09123456789", "123456")

        if expected_message:
            assert str(excinfo.value) == expected_message


def test_normalize_phone_helper():
    from accounts.services.bale_gateway import normalize_phone

    assert normalize_phone("09123456789") == "989123456789"
    assert normalize_phone("+989123456789") == "989123456789"
    assert normalize_phone("98 912 345 6789") == "989123456789"

    from accounts.services.bale_gateway import InvalidPhoneNumberError

    with pytest.raises(InvalidPhoneNumberError):
        normalize_phone("abc")


def test_gateway_v3_requires_access_key_and_bot_id():
    from accounts.services import bale_gateway

    with pytest.raises(ImproperlyConfigured):
        bale_gateway.BaleGatewayService(access_key="", bot_id=1).send_otp(
            "09123456789", "123456"
        )

    with pytest.raises(ImproperlyConfigured):
        bale_gateway.BaleGatewayService(access_key="key", bot_id=0).send_otp(
            "09123456789", "123456"
        )


@pytest.mark.django_db
def test_request_otp_rejects_invalid_formats(api_client, gateway_success):
    url = reverse("otp-request")
    for bad in ["12345", "0912345", "62801234567", "abcdefghi"]:
        response = api_client.post(url, {"phone": bad}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST, bad
    gateway_success.assert_not_called()


@pytest.mark.django_db
def test_request_otp_enforces_hourly_limit(api_client, phone, gateway_success):
    url = reverse("otp-request")

    for _ in range(30):
        PhoneOtp.objects.create(
            phone=phone,
            code_hash="salt:digest",
            expires_at=timezone.now() + datetime.timedelta(seconds=60),
        )

    response = api_client.post(url, {"phone": phone}, format="json")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    gateway_success.assert_not_called()


@pytest.mark.django_db
def test_request_otp_maps_gateway_errors(api_client, phone):
    url = reverse("otp-request")

    from accounts.services.bale_otp import (
        InsufficientBalanceError,
        InvalidPhoneError,
        NoAccountError,
    )

    cases = [
        (InvalidPhoneError(), status.HTTP_400_BAD_REQUEST),
        (NoAccountError(), status.HTTP_404_NOT_FOUND),
        (InsufficientBalanceError(), status.HTTP_402_PAYMENT_REQUIRED),
    ]

    for gateway_error, expected_status in cases:
        with patch(
            "accounts.services.otp.gateway_send_otp_v2",
            side_effect=gateway_error,
        ):
            response = api_client.post(url, {"phone": phone}, format="json")

        assert response.status_code == expected_status, gateway_error


@pytest.mark.django_db
def test_verify_creates_phone_user_and_issues_jwt(
    api_client, phone, gateway_success
):
    api_client.post(reverse("otp-request"), {"phone": phone}, format="json")

    response = api_client.post(
        reverse("otp-verify"), {"phone": phone, "code": FIXED_CODE}, format="json"
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data

    user = User.objects.get(phone=phone)
    assert user.email == f"{phone}@otp.local"
    assert not user.has_usable_password()

    record = PhoneOtp.objects.get(phone=phone)
    assert record.is_used


@pytest.mark.django_db
def test_verify_rejects_wrong_code(api_client, phone, gateway_success):
    api_client.post(reverse("otp-request"), {"phone": phone}, format="json")

    response = api_client.post(
        reverse("otp-verify"), {"phone": phone, "code": "999999"}, format="json"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    record = PhoneOtp.objects.get(phone=phone)
    assert record.attempts == 1
    assert not record.is_used


@pytest.mark.django_db
def test_verify_locks_after_max_wrong_attempts(api_client, phone, gateway_success):
    api_client.post(reverse("otp-request"), {"phone": phone}, format="json")

    verify_url = reverse("otp-verify")
    for attempt in range(4):
        response = api_client.post(
            verify_url, {"phone": phone, "code": "999999"}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, attempt

    # The 5th wrong attempt consumes the last try and locks the record.
    response = api_client.post(
        verify_url, {"phone": phone, "code": "999999"}, format="json"
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    # Even the correct code stays locked until a new one is requested.
    response = api_client.post(
        verify_url, {"phone": phone, "code": FIXED_CODE}, format="json"
    )
    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
def test_verify_rejects_expired_code(api_client, phone, gateway_success):
    api_client.post(reverse("otp-request"), {"phone": phone}, format="json")

    record = PhoneOtp.objects.get(phone=phone)
    record.expires_at = timezone.now() - datetime.timedelta(seconds=1)
    record.save(update_fields=["expires_at"])

    response = api_client.post(
        reverse("otp-verify"),
        {"phone": phone, "code": FIXED_CODE},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert User.objects.filter(phone=phone).exists() is False


@pytest.mark.django_db
def test_verify_links_phone_to_authenticated_email_account(
    api_client, phone, gateway_success
):
    email_user = User.objects.create_user(
        email="owner@example.com", password="StrongPassword@123"
    )

    api_client.post(reverse("otp-request"), {"phone": phone}, format="json")

    api_client.force_authenticate(user=email_user)
    response = api_client.post(
        reverse("otp-verify"),
        {"phone": phone, "code": FIXED_CODE},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK

    email_user.refresh_from_db()
    assert email_user.phone == phone
    assert "access" in response.data

    # Linking replaces account creation - exactly one user owns the phone.
    assert User.objects.filter(phone=phone).count() == 1


@pytest.mark.django_db
def test_used_code_cannot_verify_twice(api_client, phone, gateway_success):
    api_client.post(reverse("otp-request"), {"phone": phone}, format="json")

    first = api_client.post(
        reverse("otp-verify"),
        {"phone": phone, "code": FIXED_CODE},
        format="json",
    )
    assert first.status_code == status.HTTP_200_OK

    # The record is consumed - replaying the same code must fail.
    client = APIClient()
    second = client.post(
        reverse("otp-verify"),
        {"phone": phone, "code": FIXED_CODE},
        format="json",
    )
    assert second.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_request_otp_without_gateway_credentials_returns_503(
    api_client, phone
):
    """No BALE_OTP_* credentials -> friendly 503, not a raw 500."""

    url = reverse("otp-request")
    with patch(
        "accounts.services.otp.gateway_send_otp_v2",
        side_effect=ImproperlyConfigured("BALE_OTP_CLIENT_ID missing."),
    ):
        response = api_client.post(url, {"phone": phone}, format="json")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "BALE_OTP_CLIENT_ID missing" in response.data["detail"]
    from accounts.services.bale_otp import normalize_bale_phone

    assert normalize_bale_phone("09123456789") == "989123456789"
    assert normalize_bale_phone("+98 912 345 6789") == "989123456789"
    assert normalize_bale_phone("989123456789") == "989123456789"

    from accounts.services.bale_otp import InvalidPhoneError

    try:
        normalize_bale_phone("0912345")
    except InvalidPhoneError:
        pass
    else:
        pytest.fail("InvalidPhoneError was not raised")


# --------------------------------------------------------------------------- #
# Extra end-to-end / edge coverage
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_otp_request_throttled_per_minute(
    api_client, phone, gateway_success, monkeypatch
):
    """The real DRF scoped throttle (1/min on request-OTP) kicks in."""

    from django.core.cache import cache

    # Re-enable throttling for this test (autouse fixture disables it).
    monkeypatch.setattr(
        "rest_framework.throttling.ScopedRateThrottle.THROTTLE_RATES",
        {"otp_request": "1/min", "otp_verify": None},
    )
    cache.clear()

    try:
        first = api_client.post(
            reverse("otp-request"), {"phone": phone}, format="json"
        )
        second = api_client.post(
            reverse("otp-request"), {"phone": phone}, format="json"
        )
    finally:
        cache.clear()

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Request was throttled" in second.data["detail"]


@pytest.mark.django_db
def test_hourly_limit_ignores_records_older_than_window(
    api_client, phone, gateway_success
):
    """Only sends inside the last hour count towards the 30/hour cap."""

    url = reverse("otp-request")

    for _ in range(30):
        PhoneOtp.objects.create(
            phone=phone,
            code_hash="salt:digest",
            expires_at=timezone.now() + datetime.timedelta(seconds=60),
        )

    # Backdate all of them - outside the rolling one-hour window.
    PhoneOtp.objects.filter(phone=phone).update(
        created_date=timezone.now() - datetime.timedelta(hours=2)
    )

    response = api_client.post(url, {"phone": phone}, format="json")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.natural_code
def test_generate_code_respects_settings_length(monkeypatch):
    """"OTP_CODE_LENGTH is honoured and clamped to the 3-8 digit contract."""

    from accounts.services import otp as otp_module

    for configured, expected_length in [(6, 6), (4, 4), (1, 3), (20, 8)]:
        monkeypatch.setattr(
            settings, "OTP_CODE_LENGTH", configured, raising=False
        )
        code = otp_module._generate_code()

        assert len(code) == expected_length
        assert code.isdigit()


@pytest.mark.django_db
def test_verify_rejects_when_no_record_exists(api_client, phone, gateway_success):
    response = api_client.post(
        reverse("otp-verify"), {"phone": phone, "code": FIXED_CODE}, format="json"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_verify_rejects_disabled_account(api_client, phone, gateway_success):
    user = User.objects.create_user(
        email="disabled@example.com", password="StrongPassword@123", phone=phone
    )
    user.is_active = False
    user.save(update_fields=["is_active"])

    api_client.post(reverse("otp-request"), {"phone": phone}, format="json")

    response = api_client.post(
        reverse("otp-verify"),
        {"phone": phone, "code": FIXED_CODE},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_verify_accepts_international_phone_input(
    api_client, phone, gateway_success
):
    """Request and verify may use +98/989 formats interchangeably."""

    response = api_client.post(
        reverse("otp-request"), {"phone": "+989123456789"}, format="json"
    )
    assert response.status_code == status.HTTP_200_OK

    record = PhoneOtp.objects.get(phone=phone)  # stored normalized locally
    assert record.phone == "09123456789"

    # Verifying with the international spelling shadows the local one.
    response = api_client.post(
        reverse("otp-verify"),
        {"phone": "989123456789", "code": FIXED_CODE},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data


def test_phoneotp_is_expired_property():
    record = PhoneOtp(
        phone="09123456789",
        code_hash="salt:digest",
        expires_at=timezone.now() - datetime.timedelta(seconds=1),
    )
    assert record.is_expired is True

    record.expires_at = timezone.now() + datetime.timedelta(seconds=60)
    assert record.is_expired is False


def test_gateway_v3_module_level_send_otp(monkeypatch):
    """The module-level ``send_otp`` helper reads settings-based config."""

    from accounts.services import bale_gateway

    captured = {}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"message_id": "x.y.z"}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["headers"] = headers
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr(bale_gateway.requests, "post", fake_post)
    monkeypatch.setattr(settings, "BALE_API_ACCESS_KEY", "env-key")
    monkeypatch.setattr(settings, "BALE_BOT_ID", 555)

    result = bale_gateway.send_otp("+989123456789", 4567)

    assert result == {"message_id": "x.y.z"}
    assert captured["headers"]["api-access-key"] == "env-key"
    assert captured["json"]["bot_id"] == 555
    assert captured["json"]["phone_number"] == "989123456789"
    assert captured["json"]["message_data"] == {"otp_message": {"otp": "4567"}}


def test_gateway_v3_rejects_bad_otp_length(monkeypatch):
    """Gateway contract: the OTP value must be 3-8 digits."""

    from accounts.services import bale_gateway

    service = bale_gateway.BaleGatewayService(access_key="k", bot_id=1)

    for bad in ["12", "123456789", "abcd"]:
        with pytest.raises(ValueError):
            service.send_otp("09123456789", bad)
