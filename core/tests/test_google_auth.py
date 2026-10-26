from unittest.mock import patch

import pytest
from accounts.models import Profile
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()

GOOGLE_LOGIN_URL = reverse("google-login")
VERIFY_TOKEN_PATH = "accounts.services.google.google_id_token.verify_oauth2_token"


@pytest.fixture(autouse=True)
def google_settings(settings):
    settings.GOOGLE_OAUTH_CLIENT_ID = "test-client-id.apps.googleusercontent.com"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def google_payload():
    return {
        "iss": "https://accounts.google.com",
        "aud": "test-client-id.apps.googleusercontent.com",
        "sub": "google-user-123",
        "email": "oauth.user@example.com",
        "email_verified": True,
        "given_name": "OAuth",
        "family_name": "User",
        "picture": "https://example.com/avatar.png",
    }


def google_login(api_client, token="fake-google-id-token"):
    return api_client.post(
        GOOGLE_LOGIN_URL,
        {"id_token": token},
        format="json",
    )


@pytest.mark.django_db
def test_google_login_creates_user_and_returns_jwt(api_client, google_payload):
    with patch(VERIFY_TOKEN_PATH, return_value=google_payload):
        response = google_login(api_client)

    assert response.status_code == 200
    assert {"access", "refresh", "id", "email", "first_name"} <= set(response.data)

    user = User.objects.get(email=google_payload["email"])
    assert user.google_id == google_payload["sub"]
    assert user.has_usable_password() is False

    profile = Profile.objects.get(user=user)
    assert profile.first_name == "OAuth"
    assert profile.last_name == "User"
    assert profile.avatar_url == "https://example.com/avatar.png"

    auth_client = APIClient()
    auth_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    profile_response = auth_client.get(reverse("user-profile-me"))

    assert profile_response.status_code == 200
    assert profile_response.data["email"] == google_payload["email"]


@pytest.mark.django_db
def test_google_login_links_existing_password_account(api_client, google_payload):
    user = User.objects.create_user(
        email=google_payload["email"],
        password="StrongPassword@123",
    )
    payload = {**google_payload, "sub": "existing-account-sub"}

    with patch(VERIFY_TOKEN_PATH, return_value=payload):
        response = google_login(api_client)

    assert response.status_code == 200
    assert User.objects.filter(email__iexact=google_payload["email"]).count() == 1

    user.refresh_from_db()
    assert user.google_id == "existing-account-sub"
    assert user.check_password("StrongPassword@123") is True


@pytest.mark.django_db
def test_google_login_reuses_account_on_subsequent_logins(api_client, google_payload):
    with patch(VERIFY_TOKEN_PATH, return_value=google_payload):
        first_response = google_login(api_client)
        second_response = google_login(api_client)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert User.objects.filter(email=google_payload["email"]).count() == 1


@pytest.mark.django_db
def test_google_login_does_not_overwrite_edited_profile(api_client, google_payload):
    user = User.objects.create_user(
        email=google_payload["email"],
        password="StrongPassword@123",
    )
    user.profile.first_name = "Custom"
    user.profile.save()

    with patch(VERIFY_TOKEN_PATH, return_value=google_payload):
        response = google_login(api_client)

    assert response.status_code == 200
    user.profile.refresh_from_db()
    assert user.profile.first_name == "Custom"
    assert user.profile.last_name == "User"


@pytest.mark.django_db
def test_google_login_rejects_unverified_email(api_client, google_payload):
    payload = {**google_payload, "email_verified": False}

    with patch(VERIFY_TOKEN_PATH, return_value=payload):
        response = google_login(api_client)

    assert response.status_code == 400
    assert "id_token" in response.data
    assert not User.objects.filter(email=google_payload["email"]).exists()


@pytest.mark.django_db
def test_google_login_rejects_invalid_token(api_client):
    with patch(VERIFY_TOKEN_PATH, side_effect=ValueError("invalid token")):
        response = google_login(api_client)

    assert response.status_code == 400
    assert "id_token" in response.data


@pytest.mark.django_db
def test_google_login_requires_id_token(api_client):
    response = api_client.post(GOOGLE_LOGIN_URL, {}, format="json")

    assert response.status_code == 400
    assert "id_token" in response.data


@pytest.mark.django_db
def test_google_login_rejects_email_linked_to_another_google_account(
    api_client,
    google_payload,
):
    user = User.objects.create_user(
        email=google_payload["email"],
        password="StrongPassword@123",
    )
    user.google_id = "different-google-sub"
    user.save(update_fields=["google_id"])

    with patch(VERIFY_TOKEN_PATH, return_value=google_payload):
        response = google_login(api_client)

    assert response.status_code == 400
    assert "id_token" in response.data


@pytest.mark.django_db
def test_google_login_rejects_inactive_user(api_client, google_payload):
    user = User.objects.create_user(
        email=google_payload["email"],
        password="StrongPassword@123",
        is_active=False,
    )

    with patch(VERIFY_TOKEN_PATH, return_value=google_payload):
        response = google_login(api_client)

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.google_id is None


@pytest.mark.django_db
def test_google_login_refresh_token_is_usable(api_client, google_payload):
    with patch(VERIFY_TOKEN_PATH, return_value=google_payload):
        response = google_login(api_client)

    refresh_response = api_client.post(
        reverse("token_refresh"),
        {"refresh": response.data["refresh"]},
        format="json",
    )

    assert refresh_response.status_code == 200
    assert "access" in refresh_response.data
