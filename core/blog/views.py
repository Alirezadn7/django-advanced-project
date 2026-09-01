from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination

from .models import Category, Post, Tag
from .permissions import IsAuthorOrReadOnly
from .serializers import CategorySerializer, PostSerializer, TagSerializer


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, creating, retrieving, updating, and deleting blog Posts.

    Enforces read-only access for anonymous users and restricts modifications
    to authenticated authors.
    """
    
    # Optimize queries by preloading related author, category, and tags
    queryset = Post.objects.select_related('author' , 'category').prefetch_related('tags').all()
    serializer_class  = PostSerializer
    pagination_class = PageNumberPagination # Enable numbered pagination (e.g., ?page=2)
    lookup_field = 'slug'
    permission_classes = [permissions.IsAuthenticatedOrReadOnly , IsAuthorOrReadOnly ]
    
    # Filtering, searching, and sorting configurations
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'author', 'is_published']
    search_fields = ['title', 'content', 'author__email', 'tags__name']
    ordering_fields = ['created_date', 'published_date', 'title']
    ordering = ['-created_date']
    
    # Stamp publish date if the post is created directly with is_published=True
    def perform_create(self , serializer):
        if serializer.validated_data.get('is_published'):
            serializer.save(author=self.request.user , published_date = timezone.now())
        else:
            serializer.save(author=self.request.user)
            
class CategoryReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    
class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]