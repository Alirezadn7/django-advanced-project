import pytest
from accounts.models import Profile
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_data():
    return {
        "email": "testuser@example.com",
        "password": "StrongPassword@123"
    }


@pytest.fixture
def user(db, user_data):
    return User.objects.create_user(**user_data)


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.mark.django_db
def test_registration(api_client):
    url = reverse('user-register-list')
    new_data = {
        "email": "newuser@example.com",
        "password": "NewStrongPassword@123"
    }

    response = api_client.post(url, new_data, format='json')

    assert response.status_code == status.HTTP_201_CREATED

    new_user = User.objects.get(email=new_data['email'])
    assert Profile.objects.filter(user=new_user).exists()


@pytest.mark.django_db
def test_registration_fails_with_weak_password(api_client):
    url = reverse('user-register-list')
    weak_data = {
        "email": "weak@example.com",
        "password": "123"
    }

    response = api_client.post(url, weak_data, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_custom_jwt_login(api_client, user, user_data):
    url = reverse('custom-login')
    response = api_client.post(url, user_data, format='json')

    assert response.status_code == status.HTTP_200_OK
    assert 'access' in response.data
    assert 'refresh' in response.data
    assert response.data['email'] == user_data['email']
    assert 'first_name' in response.data


@pytest.mark.django_db
def test_retrieve_and_update_profile(auth_client, user):
    url = reverse('user-profile-me')

    get_response = auth_client.get(url)
    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.data['email'] == user.email

    update_payload = {
        "first_name": "someone",
        "bio": "does something"
    }

    patch_response = auth_client.patch(
        url,
        update_payload,
        format='json'
    )

    assert patch_response.status_code == status.HTTP_200_OK

    user.profile.refresh_from_db()
    assert user.profile.first_name == "someone"
    assert user.profile.bio == "does something"


@pytest.mark.django_db
def test_profile_unauthenticated_access_denied(api_client):
    url = reverse('user-profile-me')
    response = api_client.get(url)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_change_password_success(auth_client, user):
    url = reverse('change-password')
    payload = {
        "old_password": "StrongPassword@123",
        "new_password": "BrandNewPassword@456"
    }

    response = auth_client.post(url, payload, format='json')

    assert response.status_code == status.HTTP_200_OK

    user.refresh_from_db()
    assert user.check_password("BrandNewPassword@456") is True


@pytest.mark.django_db
def test_change_password_fails_with_incorrect_old_password(auth_client):
    url = reverse('change-password')
    payload = {
        "old_password": "WrongOldPassword!",
        "new_password": "BrandNewPassword@456"
    }

    response = auth_client.post(url, payload, format='json')

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_logout_blacklists_token(auth_client, user):
    url = reverse('logout')
    refresh = RefreshToken.for_user(user)

    payload = {"refresh": str(refresh)}
    response = auth_client.post(url, payload, format='json')

    assert response.status_code == status.HTTP_205_RESET_CONTENT

