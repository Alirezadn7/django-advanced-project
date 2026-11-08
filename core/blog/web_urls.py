from django.urls import path
from .web_views import BlogDetailView, BlogListView

urlpatterns = [
    path('', BlogListView.as_view(), name='blog-list'),
    path('post/<slug:slug>/', BlogDetailView.as_view(), name='blog-detail'),
]

