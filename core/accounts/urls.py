from django.conf import settings
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ChangePasswordAPIView,
    GoogleLoginAPIView,
    LogoutAPIView,
    OtpRequestAPIView,
    OtpTestPageView,
    OtpVerifyAPIView,
    ProfileAPIView,
    RegisterationViewset,
    TokenObtainPairView,
)

router = DefaultRouter()
router.register(r'register' , RegisterationViewset , basename='user-register')


urlpatterns = [
    path('' , include(router.urls)),
    path('login/' , TokenObtainPairView.as_view() , name='custom-login'),
    path('auth/google/' , GoogleLoginAPIView.as_view() , name='google-login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('profile/me/' , ProfileAPIView.as_view() , name = 'user-profile-me'),
    path('token/refresh/' , TokenRefreshView.as_view() , name='token_refresh'),
    path('change-password/' , ChangePasswordAPIView.as_view() , name='change-password' ),
    path('otp/request/' , OtpRequestAPIView.as_view() , name='otp-request'),
    path('otp/verify/' , OtpVerifyAPIView.as_view() , name='otp-verify'),
]

# Dev-only helper page for trying the OTP flow by hand (never in production).
if settings.DEBUG:
    urlpatterns.append(
        path('otp/test/' , OtpTestPageView.as_view() , name='otp-test-page'),
    )

