from django.contrib import admin
from .models import Post , Category

# Register your models here.

class PostAdmin(admin.ModelAdmin):
    """
    This is a class to define admin panel for Post model
    """
    
    list_display = ("title" , "author" , "category" , "created_date" , "published_date" )
    

admin.site.register(Post , PostAdmin)
admin.site.register(Category)