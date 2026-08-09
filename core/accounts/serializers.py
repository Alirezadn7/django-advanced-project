from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    """
    This is a class to serilize my user model
    """
    
    password = serializers.CharField(write_only = True)
    
    class Meta :
        model = User
        
        fields = ['id' , 'email' , 'password']
        
    def create(self, validated_data):
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        return user
    
class ProfileSerializers(serializers.ModelSerializer):
    """
    This is a class to serilize my profile model
    """
    
    
    email = serializers.EmailField(source='user.email' , read_only = True)
    
    class Meta:
        model = Profile
        fields = ['id' , 'email' , 'first_name' , 'last_name' , 'image' , 'bio']
        
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer for JWT token generation.
    Extends token payload to safely include user identity and profile metadata.
    """
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        data['id'] = self.user.id
        data['email'] = self.user.email
        try:
            data['first_name'] = self.user.profile.first_name
        except (AttributeError):    
            data['first_name'] = ""
        
        return data     
                