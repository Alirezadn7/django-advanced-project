from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Category, Post, Tag

User = get_user_model()


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class PostSerializer(serializers.ModelSerializer):
    """
    Main serializer for reading, creating, and updating blog Post entities.

    Serializes relational categories/tags and nests read-only author metadata.
    """

    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "content",
            "author",
            "image",
            "category",
            "tags",
            "is_published",
            "created_date",
            "updated_date",
            "published_date",
        ]
        # Prevent manual client overrides for auto-generated and timestamp fields
        read_only_fields = ["slug", "created_date", "updated_date", "published_date"]
