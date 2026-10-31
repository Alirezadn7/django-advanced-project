"""Client for the Bale (Bale.ai) OTP Gateway.

Official docs: https://docs.bale.ai/gateway

This service is NOT part of the regular Bot API. It works over the Bale
Gateway, based on the phone number the user registered on Bale.

Two-step flow:

1. POST {base_url}/auth/token
   Content-Type: application/x-www-form-urlencoded
   grant_type=client_credentials&client_secret=...&scope=read&client_id=...

2. POST {base_url}/send_otp
   Authorization: Bearer {access_token}
   Content-Type: application/json
   {"phone": "989123456789", "otp": 123456}

Phone numbers must be sent in the international Iranian format without a
leading zero (``09123456789`` -> ``989123456789``). The OTP code must be a
numeric value of 3 to 8 digits.

Documented errors of ``send_otp``:
    400   invalid phone number
    404   user with this phone has no Bale account
    402   insufficient balance
    500   internal server error
    gateway code 18 -> rate limit exceeded

Gateway rate limits (enforced by Bale, mirrored by our own checks):
    max 30 requests / hour   for each phone number
    max 300 requests / minute for each organization
"""

import time

import requests

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class BaleOtpError(Exception):
    """Base exception for every Bale Gateway OTP failure."""

    status_code = 502
    default_message = "Bale OTP gateway request failed."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class BaleAuthError(BaleOtpError):
    """The client_credentials token request failed."""

    default_message = "Could not authenticate with the Bale OTP gateway."


class BaleConfigError(ImproperlyConfigured):
    """BALE_OTP_CLIENT_ID / BALE_OTP_CLIENT_SECRET are missing."""


class InvalidPhoneError(BaleOtpError):
    """HTTP 400 - Bale reports the phone number as invalid."""

    status_code = 400
    default_message = "Invalid phone number (rejected by Bale gateway)."


class NoAccountError(BaleOtpError):
    """HTTP 404 - no Bale account is registered with this phone number."""

    status_code = 404
    default_message = "No Bale account exists for this phone number."


class InsufficientBalanceError(BaleOtpError):
    """HTTP 402 - the gateway wallet balance is not enough."""

    status_code = 402
    default_message = "Insufficient Bale gateway balance."


class BaleRateLimitError(BaleOtpError):
    """Gateway code 18 / HTTP 429 - rate limit exceeded."""

    status_code = 429
    default_message = "Bale gateway rate limit exceeded (code 18)."


class BaleServerError(BaleOtpError):
    """HTTP 5xx - Bale reported an internal server error."""

    status_code = 502
    default_message = "Bale gateway internal server error."


# In-process token cache: {"access_token": str, "expires_at": monotonic time}
_TOKEN_CACHE = {"access_token": None, "expires_at": 0.0}

_TOKEN_GRANT_TYPE = "client_credentials"


def normalize_bale_phone(phone) -> str:
    """Return the phone in Bale Gateway format ('989123456789').

    Accepts '09123456789' or '+989123456789' or '989123456789'.
    """

    digits = "".join(ch for ch in str(phone) if ch.isdigit())

    if digits.startswith("98") and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 11:
        return f"98{digits[1:]}"

    raise InvalidPhoneError(
        "Phone must be an Iranian mobile number like 09123456789."
    )


def _otp_settings() -> dict:
    client_id = getattr(settings, "BALE_OTP_CLIENT_ID", "")
    client_secret = getattr(settings, "BALE_OTP_CLIENT_SECRET", "")
    base_url = (getattr(settings, "BALE_OTP_BASE_URL", "") or "").rstrip("/")
    scope = getattr(settings, "BALE_OTP_SCOPE", "read")

    if not client_id or not client_secret:
        raise BaleConfigError(
            "BALE_OTP_CLIENT_ID and BALE_OTP_CLIENT_SECRET must be set "
            "to send OTP codes through the Bale gateway."
        )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "base_url": base_url or "https://safir.bale.ai/api/v2",
        "scope": scope,
    }


def _get_access_token(request_timeout: float) -> str:
    """Fetch (and cache) an access token via client_credentials grant."""

    if _TOKEN_CACHE["access_token"] and time.monotonic() < _TOKEN_CACHE["expires_at"]:
        return _TOKEN_CACHE["access_token"]

    config = _otp_settings()
    url = f"{config['base_url']}/auth/token"

    response = requests.post(
        url,
        data={
            "grant_type": _TOKEN_GRANT_TYPE,
            "client_secret": config["client_secret"],
            "scope": config["scope"],
            "client_id": config["client_id"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=request_timeout,
    )

    if response.status_code >= 500:
        raise BaleServerError()
    if response.status_code >= 400:
        raise BaleAuthError(
            f"Token request rejected by Bale gateway (HTTP {response.status_code})."
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise BaleAuthError("Malformed token response from Bale gateway.") from exc

    token = body.get("access_token")
    if not token:
        raise BaleAuthError("Token response has no access_token.")

    # Refresh slightly before the real expiry so live requests never race it.
    expires_in = int(body.get("expires_in") or 3600)
    _TOKEN_CACHE["access_token"] = token
    _TOKEN_CACHE["expires_at"] = time.monotonic() + max(expires_in - 5, 10)

    return token


def send_otp(phone, otp, request_timeout: float = 10.0) -> dict:
    """Send an OTP code to ``phone`` through the Bale gateway.

    ``phone`` may be '09...' or '98...'; it is normalized automatically.
    ``otp`` must be 3-8 digits (sent as an integer, as documented).

    Returns ``{"phone": ..., "balance": ...}`` - ``balance`` is whatever
    remaining balance info the gateway reports (or None).
    """

    bale_phone = normalize_bale_phone(phone)

    try:
        otp = int(str(otp))
    except (TypeError, ValueError) as exc:
        raise ValueError("OTP code must be numeric (3-8 digits).") from exc

    if not 3 <= len(str(otp)) <= 8:
        raise ValueError("OTP code must be 3-8 digits long.")

    token = _get_access_token(request_timeout=request_timeout)
    response = requests.post(
        f"{_otp_settings()['base_url']}/send_otp",
        json={"phone": bale_phone, "otp": otp},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=request_timeout,
    )

    if 200 <= response.status_code < 300:
        try:
            body = response.json()
        except ValueError:
            body = {}
        balance = body.get("balance") if isinstance(body, dict) else None
        return {"phone": bale_phone, "balance": balance}

    # Error mapping per official docs. Gateway code 18 may arrive with
    # various HTTP statuses, so it is sniffed from the body as well.
    try:
        body = response.json()
    except ValueError:
        body = {}

    code = body.get("code") if isinstance(body, dict) else None

    if response.status_code == 400:
        raise InvalidPhoneError()
    if response.status_code == 404:
        raise NoAccountError()
    if response.status_code == 402:
        raise InsufficientBalanceError()
    if response.status_code == 429 or code == 18:
        raise BaleRateLimitError()
    if response.status_code >= 500:
        raise BaleServerError()

    raise BaleOtpError(
        f"Unexpected gateway response (HTTP {response.status_code})."
    )
