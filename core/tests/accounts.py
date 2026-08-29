from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import Profile

User = get_user_model()


class AccountsAPITests(APITestCase):

    def setUp(self):
        self.register_url = reverse('user-register-list')
        self.login_url = reverse('custom-login')
        self.profile_url = reverse('user-profile-me')
        self.change_password_url = reverse('change-password')
        self.logout_url = reverse('logout')
        
        self.user_data = {
            "email": "testuser@example.com",
            "password": "StrongPassword@123"
        }
        
        self.user = User.objects.create_user(**self.user_data)
        
    def test_registration(self):
        new_data = {
            "email": "newuser@example.com",
            "password": "NewStrongPassword@123"
        }
        response = self.client.post(self.register_url, new_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        new_user = User.objects.get(email=new_data['email'])
        self.assertTrue(Profile.objects.filter(user=new_user).exists())
        
    def test_registration_fails_with_weak_password(self):
        weak_data = {"email": "weak@example.com", "password": "123"}
        response = self.client.post(self.register_url, weak_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_custom_jwt_login(self):
        response = self.client.post(self.login_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['email'], self.user_data['email'])
        self.assertIn('first_name', response.data)
    
    def test_retrieve_and_update_profile(self):
        self.client.force_authenticate(user=self.user)
        
        get_response = self.client.get(self.profile_url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data['email'], self.user.email)
        
        update_payload = {"first_name": "someone", "bio": "does something"}
        patch_response = self.client.patch(self.profile_url, update_payload, format='json')
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.first_name, "someone")
        self.assertEqual(self.user.profile.bio, "does something")
        
    def test_profile_unauthenticated_access_denied(self):
        get_response = self.client.get(self.profile_url)
        self.assertEqual(get_response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_change_password_success(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "old_password": "StrongPassword@123",
            "new_password": "BrandNewPassword@456"
        }
        response = self.client.post(self.change_password_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("BrandNewPassword@456"))
        
    def test_change_password_fails_with_incorrect_old_password(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "old_password": "WrongOldPassword!",
            "new_password": "BrandNewPassword@456"
        }
        response = self.client.post(self.change_password_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_logout_blacklists_token(self):
        self.client.force_authenticate(user=self.user)
        refresh = RefreshToken.for_user(self.user)
        
        payload = {"refresh": str(refresh)}
        response = self.client.post(self.logout_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)