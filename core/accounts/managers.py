"""
Custom User Model Manager.

Overrides the default Django user management logic to use email
as the primary unique identifier for authentication instead of usernames.
"""

from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    
    def create_user(self, email, password, **extra_fields):
        
        if not email:
            raise ValueError(_('The Email field must be set'))
         
        # Normalize the email domain (converts domain part to lowercase)   
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user
    
    def create_superuser(self , email , password , **extra_fields):
        
        extra_fields.setdefault("is_staff" , True)
        extra_fields.setdefault("is_superuser" , True)
        extra_fields.setdefault("is_active" , True)
        
        # Validate superuser permission constraints
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True"))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True.")) 
        return self.create_user(email, password, **extra_fields)     