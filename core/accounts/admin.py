from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserCreationForm,CustomUserChangeForm  
from .models import User , Profile
   
"""
This is a class to define admin panel for user model
"""

class ProfileInline(admin.StackedInline):
    """
    Lets you view/edit Profile fields directly on the User admin page.
    """
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile"
    fk_name = "user"
    

class CustomUserAdmin(UserAdmin):
    """
    This defines the customization of User Admin Panel
    """
    
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    inlines = (ProfileInline,)
    
    list_display = ("email", "get_first_name", "get_last_name", "is_staff", "is_active" , "created_date")
    list_filter = ("is_staff", "is_active" , "is_superuser")
    list_per_page = 25
    date_hierarchy = "created_date"
    
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_staff", "is_active","is_superuser", "groups", "user_permissions")}),
        ("Important dates" , {"fields": ("last_login" , "created_date" , "updated_date")}),
    )
    readonly_fields = ("created_date" , "updated_date" , "last_login")
    
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_active"),
        }),
    )
    
    search_fields = ("email", "profile__first_name" , "profile__last_name")
    ordering = ("email",)
    
    def  get_first_name(self , obj):
        return obj.profile.first_name
    get_first_name.short_description = "First name"
    
    def get_last_name(self , obj):
        return obj.profile.last_name
    get_last_name.short_description = "Last name"
    
admin.site.register(User, CustomUserAdmin)    