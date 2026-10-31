"""Service class for sending OTP codes via Bale's Safir v3 Gateway.

Official docs - "OTP message" section of Safir ``send_message``:

    POST https://safir.bale.ai/api/v3/send_message
    Content-Type: application/json
    api-access-key: <user-api-access-key>

    {
      "request_id": "<random-generated-string>",
      "bot_id": <your-sender-bot-id>,
      "phone_number": "<destination-phone-number>",
      "message_data": {
        "otp_message": {
          "otp": "<your-OTP>"
        }
      }
    }

    200 OK ->
    {"message_id": "BvQjaR.fIKt7kH.EXTddgYduJ2"}

Notes from the docs:

* ``bot_id`` is the sender bot whose official name is shown in the
  delivered message, with an automatic "copy OTP" button.
* The final rendered message looks like::

      رمز یک‌بارمصرف شما: 123456

      ⚠️ هشدار!
      لطفا از هویت ارسال کننده کد اطمینان حاصل فرمایید.

      از طرف: بازوی رسمی <bot name>
* ``phone_number`` must be the international Iranian format without a
  leading zero or ``+``:  ``989xxxxxxxxx``.
* ``otp`` is sent as a string in this version of the docs.
"""

import uuid

import requests

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .bale_otp import BaleOtpError


SAFIR_V3_SEND_URL = "https://safir.bale.ai/api/v3/send_message"
SAFIR_V3_BASE_URL = "https://safir.bale.ai/api/v3"


class GatewayConfigError(ImproperlyConfigured):
    """BALE_API_ACCESS_KEY / BALE_BOT_ID are missing."""


class InvalidPhoneNumberError(BaleOtpError):
    """The destination phone number is not a valid Iranian mobile number."""

    status_code = 400
    default_message = "Invalid destination phone number."


class GatewayRateLimitError(BaleOtpError):
    """The Safir gateway rejected the request due to rate limiting."""

    status_code = 429
    default_message = "Safir gateway rate limit exceeded."


class GatewayRequestError(BaleOtpError):
    """The Safir gateway returned an unhandled client error."""

    status_code = 502
    default_message = "Safir gateway rejected the request."


class GatewayServerError(BaleOtpError):
    """The Safir gateway reported an internal server error."""

    status_code = 502
    default_message = "Safir gateway internal server error."


def normalize_phone(phone) -> str:
    """Clean any phone input to Bale's required format: ``989xxxxxxxxx``.

    Strips everything but the digits, then maps:

    * ``09123456789``  -> ``989123456789``
    * ``+989123456789`` -> ``989123456789``
    * ``989123456789``  -> kept as-is
    """

    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())

    if digits.startswith("98") and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 11:
        return "98" + digits[1:]

    raise InvalidPhoneNumberError(
        "Phone must be an Iranian mobile number like 09123456789."
    )


class BaleGatewayService:
    """Service class for the Safir v3 ``send_message`` OTP endpoint."""

    def __init__(self, access_key=None, bot_id=None, timeout: float | None = None):
        self.access_key = access_key or getattr(
            settings, "BALE_API_ACCESS_KEY", ""
        )
        self.bot_id = bot_id if bot_id is not None else getattr(
            settings, "BALE_BOT_ID", 0
        )
        self.timeout = timeout if timeout is not None else 10.0

    def _build_payload(self, phone: str, otp) -> dict:
        bale_phone = normalize_phone(phone)

        otp_digits = "".join(ch for ch in str(otp or "") if ch.isdigit())

        if not 3 <= len(otp_digits) <= 8:
            raise ValueError("OTP code must be 3-8 digits long.")

        return {
            "request_id": str(uuid.uuid4()),
            "bot_id": int(self.bot_id),
            "phone_number": bale_phone,
            "message_data": {
                "otp_message": {
                    "otp": otp_digits,
                },
            },
        }

    def send_otp(self, phone, otp) -> dict:
        """Send one OTP message; returns ``{"message_id": ...}`` on success."""

        if not self.access_key:
            raise GatewayConfigError(
                "BALE_API_ACCESS_KEY must be set to use the Bale Safir gateway."
            )
        if not self.bot_id:
            raise GatewayConfigError(
                "BALE_BOT_ID (integer) must be set to use the Bale Safir gateway."
            )

        payload = self._build_payload(phone, otp)

        response = requests.post(
            SAFIR_V3_SEND_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "api-access-key": self.access_key,
            },
            timeout=self.timeout,
        )

        # 200 OK -> {"message_id": "..."}
        if 200 <= response.status_code < 300:
            try:
                body = response.json()
            except ValueError as exc:
                raise GatewayServerError(
                    "Malformed success response from Safir gateway."
                ) from exc

            message_id = body.get("message_id")

            if not message_id:
                raise GatewayServerError(
                    "Safir gateway success response has no message_id."
                )

            return {"message_id": message_id}

        if response.status_code == 400:
            raise InvalidPhoneNumberError()
        if response.status_code == 401 or response.status_code == 403:
            raise GatewayConfigError(
                f"Safir gateway rejected the API access key "
                f"(HTTP {response.status_code})."
            )
        if response.status_code == 429:
            raise GatewayRateLimitError()
        if response.status_code >= 500:
            raise GatewayServerError()

        raise GatewayRequestError(
            f"Unexpected gateway response (HTTP {response.status_code})."
        )


def send_otp(phone, otp) -> dict:
    """Convenience module-level helper using settings-based configuration."""

    return BaleGatewayService().send_otp(phone, otp)
