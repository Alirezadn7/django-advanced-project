from rest_framework import  generics , viewsets , mixins , permissions , status
from rest_framework.response import Response
from .models import Profile
from .serializers import ProfileSerializers , UserRegisterSerializer , CustomTokenObtainPairSerializer , LogoutSerializer , ChangePasswordSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

# Create your views here.
class RegisterationViewset(mixins.CreateModelMixin , viewsets.GenericViewSet):
    """
    Handles user registration.
    """
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny] # Anyone can register
    
class ProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    Handles retrieving and updating the authenticated user's profile
    """  
    queryset = Profile.objects.all() 
    serializer_class = ProfileSerializers
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        
        return self.request.user.profile
    
class TokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT authentication view.
    """
    serializer_class = CustomTokenObtainPairSerializer
    
class LogoutAPIView(generics.GenericAPIView):
    """
    Handles user logout by blacklisting the refresh token
    """
    serializer_class = LogoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self , request):
        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        
        return Response(
            {"message" : "Successfully logged out."},
            status=status.HTTP_205_RESET_CONTENT
        )

class ChangePasswordAPIView(generics.GenericAPIView):
    """
    An endpoint for changing password for logged-in users.
    Requires IsAuthenticated permission
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self , request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception= True)
        serializer.save()
        
        return Response(
                {"message": "Password updated successfully."}, 
                status=status.HTTP_200_OK
            )   
    