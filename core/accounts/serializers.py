from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .models import Profile
from .services.google import (
    GoogleTokenError,
    get_or_create_google_user,
    verify_google_id_token,
)
from .services.tokens import build_auth_payload

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
   
    password = serializers.CharField(
        write_only = True , 
        style = {'input_type' : 'password'}
        )
    
    class Meta :
        model = User
        fields = ['id' , 'email' , 'password']
        
    def validate_password(self , value):
        try :
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e))    
        
        return value
                
        
    def create(self, validated_data):
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        return user
    
class ProfileSerializers(serializers.ModelSerializer):
    
    email = serializers.EmailField(source='user.email' , read_only = True)
    
    class Meta:
        model = Profile
        fields = ['id' , 'email' , 'first_name' , 'last_name' , 'image' , 'avatar_url' , 'bio']
        
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer that appends user identifiers and basic profile
    metadata to the returned JWT response on successful login.
    """
    
    def validate(self, attrs):
        # Authenticate credentials first; this sets ``self.user``.
        super().validate(attrs)
        
        return build_auth_payload(self.user)


class GoogleLoginSerializer(serializers.Serializer):
    """Exchange a Google ID token for local SimpleJWT tokens."""
    
    id_token = serializers.CharField(write_only=True)
    
    def validate_id_token(self, value):
        try:
            payload = verify_google_id_token(value)
            self.user = get_or_create_google_user(payload)
        except GoogleTokenError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        
        return value
       
class LogoutSerializer(serializers.Serializer):
    
    refresh = serializers.CharField()
    
    def validate(self , attrs):
        self.token = attrs['refresh']
        return attrs
    
    def save(self , **kwargs):
        try :
            # Instantiate and push token into the token blacklist table
            token = RefreshToken(self.token)
            token.blacklist()
        except TokenError:
            raise serializers.ValidationError({"refresh" : "Invalid or expired refresh token."})                

class ChangePasswordSerializer(serializers.Serializer):
  
   # Common configuration for password input fields
    password_kwargs = {  
        "required": True,
        "write_only": True,
        "style": {"input_type": "password"},
    }
    
    old_password = serializers.CharField(**password_kwargs)
    new_password = serializers.CharField(**password_kwargs)
    
    def validate_old_password(self , value):
       
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value
    
    def validate_new_password(self , value):
       
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e))
        return value
    

    
            
        
        
        
    