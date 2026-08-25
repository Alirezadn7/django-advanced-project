from django.db import models
from django.utils.text import slugify
from django.conf import settings
import uuid

# Create your models here.

class Post(models.Model):
    """
    This is a class to define Post model for blog app 
    """
    
    slug = models.SlugField(max_length=256 , unique=True ,null=True, blank=True , allow_unicode=True)
    
    title = models.CharField(max_length=256)
    content = models.TextField(blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL , on_delete=models.CASCADE)
    image = models.ImageField(null=True , blank=True)
    category = models.ForeignKey("Category" , on_delete=models.SET_NULL , null = True)
    tags = models.ManyToManyField("Tag" ,  blank=True)
    is_published = models.BooleanField(default=False)
    
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    published_date = models.DateTimeField(null=True , blank=True)
    
    def save(self , *args , **kwargs ):
        if not self.slug:
            unique_id = str(uuid.uuid4())[:4]
            self.slug = f"{slugify(self.title , allow_unicode=True)}-{unique_id}"
            
        super().save(*args , **kwargs)
    
    def __str__(self):
        return self.title
    
    
class Category(models.Model):
    """
    This is a class to define Category model for blog app
    """
    
    name = models.CharField(max_length=256 , unique=True)
    slug = models.SlugField(max_length=256 , unique=True , null=True , blank=True , allow_unicode=True)
    
    def save(self , *args , **kwargs):
        if not self.slug:
            self.slug = slugify(self.name , allow_unicode=True)
            
        super().save(*args , **kwargs)
    
    def __str__(self):
        return self.name
    
class Tag(models.Model):
    """
    This is a class to define Tag model for blog app
    """
    
    name = models.CharField(max_length=256 , unique=True)
    slug = models.SlugField(max_length=256 , unique=True , null=True , blank=True , allow_unicode=True)
    
    def save(self , *args , **kwargs):
        if not self.slug:
            self.slug = slugify(self.name , allow_unicode=True)
            
        super().save(*args , **kwargs)
    
    def __str__(self):
        return self.name
    
    
