from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import RegisterationViewset , ProfileViewset

router = DefaultRouter()
router.register(r'register' , RegisterationViewset , basename='user-register')
router.register(r'profile', ProfileViewset , basename='user-profile')

urlpatterns = [
    path('' , include(router.urls)),
]
