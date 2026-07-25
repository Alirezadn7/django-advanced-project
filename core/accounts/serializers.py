from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile


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
    email = serializers.EmailField(source='user.email' , read_only = True)
    
    class Meta:
        model = Profile
        fields = ['id' , 'email' , 'first_name' , 'last_name' , 'image' , 'bio']