"""Google Sign-In helpers.

Verifies Google ID tokens and resolves them to a local user account.
The flow is stateless: the client obtains an ID token from Google and
sends it to the API, which verifies it and issues SimpleJWT tokens.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from ..models import Profile

User = get_user_model()


class GoogleTokenError(Exception):
    """Raised when a Google ID token cannot be used to authenticate."""


def verify_google_id_token(token: str) -> dict:
    """Validate a Google ID token and return its payload.

    google-auth checks the signature, issuer, audience and expiry.
    """

    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise ImproperlyConfigured(
            "GOOGLE_OAUTH_CLIENT_ID must be set to enable Google Sign-In."
        )

    try:
        payload = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_OAUTH_CLIENT_ID,
        )
    except ValueError as exc:
        raise GoogleTokenError("Invalid or expired Google token.") from exc
    except GoogleAuthError as exc:
        raise GoogleTokenError("Could not verify Google token.") from exc

    if not payload.get("email"):
        raise GoogleTokenError("Google account has no email address.")

    if payload.get("email_verified") is not True:
        raise GoogleTokenError("Google email is not verified.")

    return payload


def _sync_profile(user, payload: dict) -> None:
    """Fill missing profile fields with data from the Google account."""

    profile, _ = Profile.objects.get_or_create(user=user)

    if not profile.first_name and payload.get("given_name"):
        profile.first_name = payload["given_name"]

    if not profile.last_name and payload.get("family_name"):
        profile.last_name = payload["family_name"]

    if payload.get("picture"):
        profile.avatar_url = payload["picture"]

    profile.save()


@transaction.atomic
def get_or_create_google_user(payload: dict) -> User:
    """Return the local user matching a verified Google token payload.

    An existing password account is linked automatically only when the
    Google email has been verified (checked in ``verify_google_id_token``).
    """

    google_id = payload.get("sub")
    email = (payload.get("email") or "").strip().lower()

    if not google_id or not email:
        raise GoogleTokenError("Google token is missing required account information.")

    user = User.objects.filter(google_id=google_id).first()

    if user is not None and not user.is_active:
        raise GoogleTokenError("This account is disabled.")

    if user is None:
        user = User.objects.filter(email__iexact=email).first()

        if user is not None:
            if not user.is_active:
                raise GoogleTokenError("This account is disabled.")
            if user.google_id and user.google_id != google_id:
                raise GoogleTokenError(
                    "This email is already linked to another Google account."
                )
            user.google_id = google_id
            user.save(update_fields=["google_id"])
        else:
            try:
                # Nested atomic block keeps the outer transaction usable
                # if two concurrent logins try to create the same user.
                with transaction.atomic():
                    user = User.objects.create_google_user(
                        email=email,
                        google_id=google_id,
                    )
            except IntegrityError as exc:
                user = User.objects.filter(google_id=google_id).first()
                if user is None:
                    raise GoogleTokenError(
                        "Could not create an account for this Google user."
                    ) from exc

    _sync_profile(user, payload)
    return user
