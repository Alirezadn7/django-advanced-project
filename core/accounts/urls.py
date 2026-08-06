from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import RegisterationViewset , ProfileViewset , CustomLoginView
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'register' , RegisterationViewset , basename='user-register')
router.register(r'profile', ProfileViewset , basename='user-profile')

urlpatterns = [
    path('' , include(router.urls)),
    path('login/' , CustomLoginView.as_view() , name='custom_login'),
    path('token/refresh/' , TokenRefreshView.as_view() , name='token_refresh'),
]
