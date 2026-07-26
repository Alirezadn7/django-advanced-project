from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Post,Category

User = get_user_model()

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id' , 'email']
        
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id' , 'name']
        
class PostSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only = True)   
    
    class Meta:
        model = Post
        fields =[
            'id' , 'title' , 'content' , 'author' , 'image',
            'category' , 'publish' , 'created_date' , 'updated_date',
            'published_date' 
        ]    
        