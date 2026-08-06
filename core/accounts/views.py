from rest_framework import viewsets , mixins , permissions
from .models import Profile
from .serializers import ProfileSerializers , UserRegisterSerializer , CustomTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

# Create your views here.
class RegisterationViewset(mixins.CreateModelMixin , viewsets.GenericViewSet):
    """
    Handles user registration.
    """
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny] # Anyone can register
    
class ProfileViewset(mixins.RetrieveModelMixin , mixins.UpdateModelMixin , viewsets.GenericViewSet):
    """
    Handles retrieving and updating profile
    """    
    serializer_class = ProfileSerializers
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        
        return self.request.user.profile
    
class CustomLoginView(TokenObtainPairView):
    """
    Custom JWT authentication view.
    """
    serializer_class = CustomTokenObtainPairSerializer
    