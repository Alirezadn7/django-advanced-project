from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryReadOnlyViewSet, PostViewSet, TagViewSet

router = DefaultRouter()
router.register(r'posts' , PostViewSet , basename='post')
router.register(r'categories', CategoryReadOnlyViewSet, basename='category')
router.register(r'tags', TagViewSet, basename='tag')

urlpatterns = [
    path('' ,  include(router.urls)),
]
