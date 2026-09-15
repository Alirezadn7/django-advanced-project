import pytest
from blog.models import Category, Post, Tag
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()



@pytest.fixture
def api_client():
    return APIClient()



@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="testuser@example.com",
        password="StrongPassword@123",
    )


@pytest.fixture
def another_user(db):
    return User.objects.create_user(
        email="otheruser@example.com",
        password="StrongPassword@123",
    )


@pytest.fixture
def auth_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def other_auth_client(another_user):
    # NOTE: builds its own APIClient instead of reusing `api_client`,
    # because force_authenticate mutates the shared instance and would
    # overwrite the authentication of `auth_client` in the same test.
    client = APIClient()
    client.force_authenticate(user=another_user)
    return client


@pytest.fixture
def category(db):
    return Category.objects.create(name="Django")


@pytest.fixture
def another_category(db):
    return Category.objects.create(name="Python")


@pytest.fixture
def tag(db):
    return Tag.objects.create(name="Backend")




@pytest.mark.django_db
def test_create_post(auth_client, user, category, tag):
    url = reverse('post-list')
    post_data = {
        "title": "test title",
        "content": "test content",
        "category": category.id,
        "tags": [tag.id],
        "is_published": True,
    }
    
    response = auth_client.post(url, post_data, format='json')
    
    assert response.status_code == status.HTTP_201_CREATED
    
    # Ensure slug is automatically populated from title
    assert response.data['slug'] is not None
    assert "test-title" in response.data['slug']
    
    # Verify publication timestamp and author assignment defaults
    assert response.data['is_published'] is True
    assert response.data['published_date'] is not None
    assert response.data['author']['email'] == user.email
    assert Post.objects.filter(title=post_data["title"]).exists()

@pytest.mark.django_db
def test_publish_draft_via_update_sets_published_date(auth_client, user):
    post = Post.objects.create(
        title="Draft Post",
        content="Content",
        author=user,
        is_published=False,
    )
    assert post.published_date is None

    url = reverse('post-detail', kwargs={'slug': post.slug})
    response = auth_client.patch(url, {"is_published": True}, format='json')

    assert response.status_code == status.HTTP_200_OK
    post.refresh_from_db()
    assert post.is_published is True
    assert post.published_date is not None

@pytest.mark.django_db
def test_create_post_without_publish(auth_client, user):
    url = reverse('post-list')
    post_data = {
        "title": "draft title",
        "content": "test content",
        "is_published": False,
    }
    
    response = auth_client.post(url, post_data, format='json')
    
    assert response.status_code == status.HTTP_201_CREATED
    # Drafts must not have an active publication timestamp
    assert response.data['is_published'] is False
    assert response.data['published_date'] is None


@pytest.mark.django_db
def test_unauthenticated_post_create_fails(api_client):
    url = reverse('post-list')
    post_data = {
        "title": "anonymous title",
        "content": "test content",
    }
    
    response = api_client.post(url, post_data, format='json')
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert Post.objects.count() == 0


@pytest.mark.django_db
def test_only_author_can_edit_or_delete(auth_client, other_auth_client, user):
    post = Post.objects.create(
        title="Author Post",
        content="Content",
        author=user,
        is_published=True,
    )
    detail_url = reverse('post-detail', kwargs={'slug': post.slug})
    
    # Verify object-level permission enforcement against non-authors (IsAuthorOrReadOnly)
    forbidden_patch = other_auth_client.patch(detail_url, {"title": "Hacked"}, format='json')
    assert forbidden_patch.status_code == status.HTTP_403_FORBIDDEN
    
    forbidden_delete = other_auth_client.delete(detail_url)
    assert forbidden_delete.status_code == status.HTTP_403_FORBIDDEN
    assert Post.objects.filter(pk=post.pk).exists()
    
    # Validate update access for the resource owner
    author_patch = auth_client.patch(detail_url, {"title": "Updated Title"}, format='json')
    assert author_patch.status_code == status.HTTP_200_OK
    post.refresh_from_db()
    assert post.title == "Updated Title"
    
    # Validate deletion access for the resource owner
    author_delete = auth_client.delete(detail_url)
    assert author_delete.status_code == status.HTTP_204_NO_CONTENT
    assert not Post.objects.filter(pk=post.pk).exists()


@pytest.mark.django_db
def test_post_filter_and_slug_lookup(api_client, user, category, another_category):
    post_django = Post.objects.create(
        title="Django Tutorial",
        content="Guide to DRF",
        author=user,
        category=category,
        is_published=True,
    )
    post_python = Post.objects.create(
        title="Python Basics",
        content="Learn Python",
        author=user,
        category=another_category,
        is_published=True,
    )
    post_draft = Post.objects.create(
        title="Draft Note",
        content="Not published",
        author=user,
        category=category,
        is_published=False,
    )
    
    list_url = reverse('post-list')
    
    # Verify exact match filtering via django-filter
    filter_url = f"{list_url}?category={category.id}&is_published=true"
    response = api_client.get(filter_url)
    assert response.status_code == status.HTTP_200_OK
    
    # Safely handle both paginated and non-paginated API responses
    results = response.data.get('results', response.data)
    assert len(results) == 1
    assert results[0]['id'] == post_django.id
    
    # Validate full-text search backend (SearchFilter) on title field
    search_url = f"{list_url}?search=Basics"
    search_response = api_client.get(search_url)
    search_results = search_response.data.get('results', search_response.data)
    assert len(search_results) == 1
    assert search_results[0]['id'] == post_python.id


@pytest.mark.django_db
def test_category_and_tag_endpoints(api_client, auth_client, category, tag):
    category_list_url = reverse('category-list')
    tag_list_url = reverse('tag-list')
    
    # Ensure Category endpoint is strictly read-only (ReadOnlyModelViewSet)
    cat_get = api_client.get(category_list_url)
    assert cat_get.status_code == status.HTTP_200_OK
    
    cat_post = auth_client.post(category_list_url, {"name": "New Category"}, format='json')
    assert cat_post.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    # Verify authenticated write access on Tag endpoint
    tag_get = api_client.get(tag_list_url)
    assert tag_get.status_code == status.HTTP_200_OK
    
    tag_post = auth_client.post(tag_list_url, {"name": "New Tag"}, format='json')
    assert tag_post.status_code == status.HTTP_201_CREATED
    assert Tag.objects.filter(name="New Tag").exists()
    
    