from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class User(AbstractBaseUser , PermissionsMixin):
   
    email = models.EmailField(_("email address") , unique=True)
    phone = models.CharField(
        _("phone number"),
        max_length=15,
        unique=True,
        null=True,
        blank=True,
    )
    google_id = models.CharField(
        _("google account id"),
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )
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
    avatar_url = models.URLField(blank=True , default="")
    bio = models.TextField(blank=True , default="")
    
    def __str__(self):
        return self.user.email
    
class PhoneOtp(models.Model):
    """One OTP code sent to a phone through the Bale gateway.

    The code itself is never stored - only a salted SHA-256 hash
    (``"<salt>:<hex digest>"``). At most ``settings.OTP_PHONE_HOURLY_LIMIT``
    records per hour and phone keep the Bale gateway rate contract.
    """

    phone = models.CharField(max_length=15 , db_index=True)
    code_hash = models.CharField(max_length=140)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_date"]
        indexes = [
            models.Index(fields=["phone" , "created_date"]),
        ]

    def __str__(self):
        return f"OTP for {self.phone} at {self.created_date:%Y-%m-%d %H:%M}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


# Automatically trigger profile creation whenever a User instance is saved    
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
   
    if created:
        Profile.objects.create(user=instance)
    
        
        
