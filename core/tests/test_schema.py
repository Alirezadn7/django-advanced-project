import os

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_openapi_schema_endpoint_returns_valid_schema():
    client = APIClient()
    response = client.get(reverse("schema"), HTTP_ACCEPT="application/json")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["openapi"].startswith("3.")
    assert data["info"]["title"] == "Django Advanced Blog API"

    expected_paths = [
        "/api/accounts/register/",
        "/api/accounts/login/",
        "/api/accounts/auth/google/",
        "/api/accounts/otp/request/",
        "/api/accounts/otp/verify/",
        "/api/accounts/change-password/",
        "/api/accounts/profile/me/",
        "/api/blog/posts/",
        "/api/blog/categories/",
        "/api/blog/tags/",
    ]
    for path in expected_paths:
        assert path in data["paths"], f"Missing {path} in OpenAPI schema"


@pytest.mark.django_db
def test_swagger_ui_and_redoc_endpoints():
    client = APIClient()

    swagger_res = client.get(reverse("swagger-ui"))
    assert swagger_res.status_code == status.HTTP_200_OK
    assert "swagger-ui" in swagger_res.content.decode("utf-8").lower()

    redoc_res = client.get(reverse("redoc"))
    assert redoc_res.status_code == status.HTTP_200_OK
    redoc_html = redoc_res.content.decode("utf-8")
    assert "redoc" in redoc_html.lower()
    assert "https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js" in redoc_html


@pytest.mark.django_db
def test_spectacular_command_validates_without_warnings():
    call_command(
        "spectacular",
        file=os.devnull,
        validate=True,
        fail_on_warn=True,
    )
