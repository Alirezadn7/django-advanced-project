from django.views.generic import TemplateView
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Profile
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    GoogleLoginSerializer,
    LogoutSerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    ProfileSerializers,
    UserRegisterSerializer,
)
from .services.otp import OtpError
from .services.accounts import update_account
from .services.tokens import build_auth_payload


class RegisterationViewset(mixins.CreateModelMixin , viewsets.GenericViewSet):
    
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny] # Anyone can register
    
class ProfileAPIView(generics.RetrieveUpdateAPIView):
     
    queryset = Profile.objects.all() 
    serializer_class = ProfileSerializers
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        
        return self.request.user.profile
    
class TokenObtainPairView(TokenObtainPairView):
    
    serializer_class = CustomTokenObtainPairSerializer

class GoogleLoginAPIView(APIView):
    """Authenticate with a Google ID token and return SimpleJWT tokens."""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        return Response(
            build_auth_payload(serializer.user),
            status=status.HTTP_200_OK,
        )
    
class LogoutAPIView(generics.GenericAPIView):
    
    serializer_class = LogoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self , request):
        serializer = self.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        
        return Response(
            {"message" : "Successfully logged out."},
            status=status.HTTP_205_RESET_CONTENT
        )

class OtpRequestAPIView(APIView):
    """Send an OTP code to a phone via the Bale gateway.

    Throttled hard locally to respect the documented gateway contract
    (30 requests/hour per phone, no sudden bursts).
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_request"

    def post(self, request, *args, **kwargs):
        serializer = OtpRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = serializer.save()
        except OtpError as exc:
            # Gateway errors keep their mapped HTTP status (400/402/404/429/502).
            return Response({"detail": str(exc)}, status=exc.status_code)

        return Response(
            {
                "detail": result["detail"],
                "expires_in": result["expires_in"],
                "message_id": result.get("message_id"),
                # The gateway wallet balance (legacy v2) is deliberately not
                # exposed: this is a public, unauthenticated endpoint.
            },
            status=status.HTTP_200_OK,
        )


class OtpVerifyAPIView(APIView):
    """Verify the OTP code and return SimpleJWT tokens.

    If the caller is already authenticated and their account has no phone
    yet, the verified number is linked to that account (conditional
    linking) instead of creating a new phone-only account.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_verify"

    def post(self, request, *args, **kwargs):
        serializer = OtpVerifySerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        try:
            payload = serializer.save()
        except OtpError as exc:
            return Response({"detail": str(exc)}, status=exc.status_code)

        return Response(payload, status=status.HTTP_200_OK)


class OtpTestPageView(TemplateView):
    """Simple browser page to try the OTP flow by hand."""

    template_name = "accounts/otp_test.html"


class ChangePasswordAPIView(APIView):
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self , request ,*args , **kwargs):
        serializer = ChangePasswordSerializer(data = request.data , context={'request':request})
        serializer.is_valid(raise_exception=True)
        update_account(user=request.user , password=serializer.validated_data['new_password'])
       
        return Response(
                {"message": "Password updated successfully."}, 
                status=status.HTTP_200_OK
            )   
    