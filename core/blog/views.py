from rest_framework import viewsets, permissions
from .models import Post
from .serializers import PostSerializer

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class  = PostSerializer
    permissions_class = [permissions.IsAuthenticatedOrReadOnly]
    
    def perform_create(self , serializer):
        serializer.save(author=self.request.user)


