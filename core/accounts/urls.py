from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import ( 
    RegisterationViewset ,
    ProfileAPIView ,
    TokenObtainPairView ,
    LogoutAPIView,
    ChangePasswordAPIView
    )
from rest_framework_simplejwt.views import TokenRefreshView

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

