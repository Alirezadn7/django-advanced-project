from rest_framework import  generics , viewsets , mixins , permissions , status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Profile
from .serializers import ProfileSerializers , UserRegisterSerializer , CustomTokenObtainPairSerializer , LogoutSerializer , ChangePasswordSerializer
from rest_framework_simplejwt.views import TokenObtainPairView 
from .services.accounts import update_account


class RegisterationViewset(mixins.CreateModelMixin , viewsets.GenericViewSet):
    
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny] # Anyone can register
    
class ProfileAPIView(generics.RetrieveUpdateAPIView):
     
    queryset = Profile.objects.all() 
    serializer_class = ProfileSerializers
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        
        return self.request.user.profile
    
class TokenObtainPairView(TokenObtainPairView):
    
    serializer_class = CustomTokenObtainPairSerializer
    
class LogoutAPIView(generics.GenericAPIView):
    
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

class ChangePasswordAPIView(APIView):
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self , request ,*args , **kwargs):
        serializer = ChangePasswordSerializer(data = request.data , context={'request':request})
        serializer.is_valid(raise_exception=True)
        update_account(user=request.user , password=serializer.validated_data['new_password'])
       
        return Response(
                {"message": "Password updated successfully."}, 
                status=status.HTTP_200_OK
            )   
    