from django.utils import timezone
from rest_framework import permissions, viewsets

from .models import Post
from .permissions import IsAuthorOrReadOnly
from .serializers import PostSerializer


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, creating, retrieving, updating, and deleting blog Posts.

    Enforces read-only access for anonymous users and restricts modifications
    to authenticated authors.
    """
    
    queryset = Post.objects.all()
    serializer_class  = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly , IsAuthorOrReadOnly ]
    
    # Stamp publish date if the post is created directly with is_published=True
    def perform_create(self , serializer):
        if serializer.validated_data.get('is_published'):
            serializer.save(author=self.request.user , published_date = timezone.now())
        else:
            serializer.save(author=self.request.user)


