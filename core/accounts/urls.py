from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ChangePasswordAPIView,
    LogoutAPIView,
    ProfileAPIView,
    RegisterationViewset,
    TokenObtainPairView,
)

router = DefaultRouter()
router.register(r'register' , RegisterationViewset , basename='user-register')


urlpatterns = [
    path('' , include(router.urls)),
    path('login/' , TokenObtainPairView.as_view() , name='custom-login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('profile/me/' , ProfileAPIView.as_view() , name = 'user-profile-me'),
    path('token/refresh/' , TokenRefreshView.as_view() , name='token_refresh'),
    path('change-password/' , ChangePasswordAPIView.as_view() , name='change-password' ),
]

