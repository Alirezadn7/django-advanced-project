from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import User

"""
This is a form to create user in django admin panel.
It's used for creating new users and updating existing ones,
as well as validating data before saving it into
the database or changing an already saved one respectively.  
"""


class CustomUserCreationForm(UserCreationForm):
     """
     This is a form to create user in django admin panel.
     It's used for creating new users and updating existing ones,
     as well as valid
     """
     
     class Meta:
         model = User
         fields = ("email",) 
         
class CustomUserChangeForm(UserChangeForm):
    """
    This is a form to change user in django admin panel. 
    It's used for updating existing users and validating 
    data before saving it into the database or changing 
    an already saved one respectively.
    """   

    class Meta:
        model = User
        fields = ("email",)