"""Shared JWT response builder for every login method."""

from rest_framework_simplejwt.tokens import RefreshToken


def build_auth_payload(user) -> dict:
    """Build the access/refresh pair and public user data.

    Both password login and Google login return this exact shape.
    """

    refresh = RefreshToken.for_user(user)
    profile = getattr(user, "profile", None)

    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "id": user.id,
        "email": user.email,
        "first_name": profile.first_name if profile is not None else "",
    }
