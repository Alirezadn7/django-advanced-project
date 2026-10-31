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
from .services.otp import (
    OtpError,
    normalize_local_phone,
    request_otp,
    verify_otp,
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

class OtpRequestSerializer(serializers.Serializer):
    """Ask the Bale gateway to send an OTP code to a phone number."""

    phone = serializers.CharField()

    def validate_phone(self, value):
        try:
            return normalize_local_phone(value)
        except OtpError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def save(self, **kwargs):
        # ``request_otp`` may raise mapped gateway errors (429/404/402/...);
        # the API view converts them into the proper HTTP status codes.
        return request_otp(self.validated_data["phone"])


class OtpVerifySerializer(serializers.Serializer):
    """Check the OTP code and issue SimpleJWT tokens for the user."""

    phone = serializers.CharField()
    code = serializers.CharField()

    def validate_phone(self, value):
        try:
            return normalize_local_phone(value)
        except OtpError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_code(self, value):
        code = "".join(ch for ch in value if ch.isdigit())
        if not 3 <= len(code) <= 8:
            raise serializers.ValidationError(
                "The verification code must be 3-8 digits."
            )
        return code

    def save(self, **kwargs):
        self.user = verify_otp(
            self.validated_data["phone"],
            self.validated_data["code"],
            linking_user=self.context.get("request").user
            if self.context.get("request") is not None
            else None,
        )

        return build_auth_payload(self.user)


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
    

    
            
        
        
        
    