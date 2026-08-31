from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class User(AbstractBaseUser , PermissionsMixin):
   
    email = models.EmailField(_("email address") , unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    created_date = models.DateTimeField(default=timezone.now)
    updated_date = models.DateTimeField(auto_now=True)
    
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  
    
    objects = CustomUserManager()
    
    
    def __str__(self):
        return self.email

class Profile(models.Model):
    
    user = models.OneToOneField(User , on_delete=models.CASCADE)
    first_name = models.CharField(max_length=255 ,  blank=True , default="")
    last_name = models.CharField(max_length=255 , blank=True , default="")
    image = models.ImageField(blank=True , null=True)
    bio = models.TextField(blank=True , default="")
    
    def __str__(self):
        return self.user.email
    
# Automatically trigger profile creation whenever a User instance is saved    
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
   
    if created:
        Profile.objects.create(user=instance)
    
        
        
