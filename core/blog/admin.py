from django.contrib import admin

from .models import Category, Post, Tag


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'author', 
        'category', 
        'is_published', 
        'published_date', 
        'created_date'
    )
    

    list_editable = ('is_published',)
    
    list_filter = ('is_published', 'category', 'tags', 'created_date')
    
    
    search_fields = ('title', 'content', 'author__email', 'tags__name')
    
    # Provides a side-by-side UI widget with search for ManyToMany fields (e.g. tags)
    filter_horizontal = ('tags',)
    
    date_hierarchy = 'created_date'
    readonly_fields = ('created_date', 'updated_date')
    
    # Group and organize form fields into collapsible and structured sections
    fieldsets = (
        ('Main Content', {
            'fields': ('title', 'slug', 'content', 'image')
        }),
        ('Taxonomies & Author', {
            'fields': ('author', 'category', 'tags')
        }),
        ('Publication Details', {
            'fields': ('is_published', 'published_date', 'created_date', 'updated_date'),
            'classes': ('collapse',), # Collapsed by default to keep the form clean
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    # Auto-generate slug from name
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}