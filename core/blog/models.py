from django.db import models
from django.conf import settings

# Create your models here.

class Post(models.Model):
    """
    This is a class to define Post model for blog app
    """
    title = models.CharField(max_length=256)
    content = models.TextField(blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL , on_delete=models.CASCADE)
    image = models.ImageField(null=True , blank=True)
    category = models.ForeignKey("Category" , on_delete=models.SET_NULL , null = True)
    publish= models.BooleanField()
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    published_date = models.DateTimeField(null=True , blank=True)
    
    
    def __str__(self):
        return self.title
    
    
class Category(models.Model):
    """
    This is a class to define Category model for blog app
    """
    
    name = models.CharField(max_length=256)
    
    
    def __str__(self):
        return self.name
    
    
