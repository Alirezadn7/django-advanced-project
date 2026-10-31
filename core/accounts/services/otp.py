"""Phone OTP login flow backed by the Bale Gateway.

Responsibilities:

* validate/normalize Iranian mobile numbers,
* enforce rate limits (Bale allows 30/hour per phone, 300/min per org),
* generate cryptographically secure OTP codes (3-8 digits),
* store only a salted hash of each code,
* progressive lock-out after repeated wrong attempts,
* resolve the local user account and issue SimpleJWT tokens via
  :func:`accounts.services.tokens.build_auth_payload`.
"""

import hashlib
import hmac
import secrets
import re
import string

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from ..models import PhoneOtp
from .bale_otp import (
    BaleOtpError,
    send_otp as gateway_send_otp_v2,
)
from .bale_gateway import send_otp as gateway_send_otp_v3

User = get_user_model()


class OtpError(Exception):
    """Base error for the OTP flow; ``status_code`` maps to a DRF answer."""

    status_code = 400

    def __init__(self, message=None, status_code=None):
        super().__init__(message or self.default_message)

        if status_code is not None:
            self.status_code = status_code

    default_message = "OTP request failed."


class OtpInvalidPhoneError(OtpError):
    status_code = 400
    default_message = "Enter a valid Iranian mobile number (09xxxxxxxxx)."


class OtpRateLimitError(OtpError):
    status_code = 429
    default_message = "Too many OTP requests for this phone. Try again later."


class OtpInvalidCodeError(OtpError):
    status_code = 400
    default_message = "Invalid or expired verification code."


class OtpLockedError(OtpError):
    status_code = 429
    default_message = "Too many wrong attempts. Request a new code."


class OtpDeliveryError(OtpError):
    """The Bale gateway rejected the send; keeps the gateway status code."""

    default_message = "Could not deliver the OTP code."

    def __init__(self, gateway_error: BaleOtpError):
        super().__init__(
            str(gateway_error) or self.default_message,
            status_code=gateway_error.status_code,
        )


_PHONE_RE = re.compile(r"^09\d{9}$")
_DIGITS = string.digits


def normalize_local_phone(phone) -> str:
    """Return the phone as '09xxxxxxxxx' or raise OtpInvalidPhoneError."""

    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())

    if digits.startswith("98") and len(digits) == 12:
        digits = "0" + digits[2:]

    if not _PHONE_RE.match(digits):
        raise OtpInvalidPhoneError()

    return digits


def _hash_code(code: str) -> str:
    """Salted SHA-256 hash in the reversible '<salt>:<digest>' format."""

    salt = secrets.token_hex(8)
    digest = hashlib.sha256(f"{salt}{code}".encode()).hexdigest()
    return f"{salt}:{digest}"


def _check_hash(code: str, code_hash: str) -> bool:
    """Verify a stored hash with a constant-time comparison.

    ``hmac.compare_digest`` removes the (very small but real) timing
    side-channel of a plain ``==`` digest comparison.
    """

    salt, digest = (code_hash.split(":") + [""])[:2]
    computed = hashlib.sha256(f"{salt}{code}".encode()).hexdigest()
    return hmac.compare_digest(computed, digest)


def _generate_code() -> str:
    length = int(getattr(settings, "OTP_CODE_LENGTH", 6))

    # Documented gateway contract: OTP values are 3 to 8 digits.
    length = max(3, min(length, 8))

    # ``secrets`` uses the CSPRNG - unpredictable per phone and per request.
    return "".join(secrets.choice(_DIGITS) for _ in range(length))


def _deliver_code(phone: str, code: str) -> dict:
    """Deliver the code through the configured Bale gateway.

    ``BALE_OTP_GATEWAY`` selects the transport:

    * ``v3`` (default) - Safir ``send_message`` bot OTP message
      (:mod:`accounts.services.bale_gateway`),
    * ``v2`` - OAuth ``client_credentials`` + ``/send_otp``
      (:mod:`accounts.services.bale_otp`).
    """

    gateway = (getattr(settings, "BALE_OTP_GATEWAY", "v3") or "v3").lower()

    try:
        if gateway == "v2":
            return gateway_send_otp_v2(phone, code)
        return gateway_send_otp_v3(phone, code)
    except ImproperlyConfigured as exc:
        # Gateway credentials are not configured on this deployment.
        raise OtpError(str(exc), status_code=503) from exc
    except BaleOtpError as exc:
        raise OtpDeliveryError(exc) from exc


def request_otp(phone) -> dict:
    """Generate, store and send an OTP code for ``phone``.

    Raises :class:`OtpRateLimitError` when the per-phone hourly limit is
    reached, or :class:`OtpDeliveryError` when the gateway fails.
    """

    phone = normalize_local_phone(phone)

    hourly_limit = int(getattr(settings, "OTP_PHONE_HOURLY_LIMIT", 30))
    window_start = timezone.now() - timezone.timedelta(hours=1)
    recent_count = PhoneOtp.objects.filter(
        phone=phone,
        created_date__gte=window_start,
    ).count()

    if recent_count >= hourly_limit:
        raise OtpRateLimitError(
            "Hourly OTP limit reached for this phone"
            f" ({hourly_limit} per hour). Try again later."
        )

    code = _generate_code()
    ttl = int(getattr(settings, "OTP_TTL_SECONDS", 120))

    PhoneOtp.objects.create(
        phone=phone,
        code_hash=_hash_code(code),
        expires_at=timezone.now() + timezone.timedelta(seconds=ttl),
    )

    # Dispatches to the configured Safir gateway (v3 default, v2 legacy).
    result = _deliver_code(phone, code)

    response = {
        "detail": "OTP code sent successfully.",
        "expires_in": ttl,
    }

    # v3 reports a message_id; v2 (legacy) may report the wallet balance.
    if "message_id" in result:
        response["message_id"] = result["message_id"]
    if result.get("balance") is not None:
        response["balance"] = result["balance"]

    return response


def verify_otp(phone, code, linking_user=None):
    """Verify ``code`` for ``phone`` and return the authenticated ``User``.

    ``linking_user`` (optional) is an already authenticated user without a
    phone number; if the phone is not taken yet, the verified number is
    attached to that account instead of creating a new one.
    """

    phone = normalize_local_phone(phone)
    code = "".join(ch for ch in str(code or "") if ch.isdigit())

    record = (
        PhoneOtp.objects.filter(phone=phone)
        .order_by("-created_date")
        .first()
    )

    max_attempts = int(getattr(settings, "OTP_MAX_ATTEMPTS", 5))

    if record is None:
        raise OtpInvalidCodeError()

    if record.attempts >= max_attempts:
        raise OtpLockedError()

    if record.is_used:
        raise OtpInvalidCodeError()

    if record.is_expired:
        raise OtpInvalidCodeError("This verification code has expired.")

    if not _check_hash(code, record.code_hash):
        # Atomic increment: parallel wrong guesses each bump the counter,
        # so the lock-out cannot be bypassed with concurrent requests.
        PhoneOtp.objects.filter(pk=record.pk).update(attempts=F("attempts") + 1)
        record.refresh_from_db(fields=["attempts"])

        if record.attempts >= max_attempts:
            raise OtpLockedError()

        raise OtpInvalidCodeError()

    # Atomically claim the code: exactly one concurrent verification can
    # flip ``is_used``, so a valid code can never be replayed in parallel.
    claimed = PhoneOtp.objects.filter(
        pk=record.pk,
        is_used=False,
    ).update(is_used=True)

    if not claimed:
        raise OtpInvalidCodeError()

    return _resolve_user(phone, linking_user=linking_user)


def _resolve_user(phone, linking_user=None):
    """Find or build the account that owns the verified phone number."""

    user = User.objects.filter(phone=phone).first()

    if user is not None:
        if not user.is_active:
            raise OtpError("This account is disabled.", status_code=403)
        return user

    # Conditional linking: an authenticated caller without a phone yet
    # claims the verified number for the existing (email/password) account.
    if (
        linking_user is not None
        and linking_user.is_authenticated
        and not linking_user.phone
    ):
        linking_user.phone = phone
        linking_user.save(update_fields=["phone"])
        return linking_user

    try:
        # Nested atomic block keeps things usable if two concurrent
        # verifications race to create the same phone user.
        with transaction.atomic():
            return User.objects.create_phone_user(phone=phone)
    except IntegrityError:
        user = User.objects.filter(phone=phone).first()
        if user is None:
            raise OtpError("Could not create an account for this phone.")
        return user
