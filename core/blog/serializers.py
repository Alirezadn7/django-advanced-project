from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Post,Category,Tag

User = get_user_model()

class AuthorSerializer(serializers.ModelSerializer):
    """
    Helper serializer to represent nested author details in blog post API responses
    """
    
    class Meta:
        model = User
        fields = ['id' , 'email']
        
class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for managing blog post categories
    """
    
    class Meta:
        model = Category
        fields = ['id' , 'name']
        
class TagSerializer(serializers.ModelSerializer):
    """
    Serializer for managing blog post tags  
    """
    
    
    class Meta:
        model = Tag
        fields = ['id' , 'name']  
        
class PostSerializer(serializers.ModelSerializer):
    """
    Main serializer for the Post model.
    Handles data serialization , validation , and nested author representaion.
    """
    
    author = AuthorSerializer(read_only = True)   
    
    class Meta:
        model = Post
        fields =[
            'id' ,'title','slug' , 'content' , 'author' , 'image',
            'category' ,'tags', 'is_published' , 'created_date' , 'updated_date',
            'published_date' 
        ]
        read_only_fields = ['slug','created_date' , 'updated_date' , 'published_date']      
        
  
        