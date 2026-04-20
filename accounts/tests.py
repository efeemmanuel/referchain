from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from hospitals.models import Hospital


class AuthTests(TestCase):
    """
    Tests for registration and login endpoints.
    """

    def setUp(self):
        """
        Runs before every test.
        Creates a fresh API client for making requests.
        """
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')

        # Valid registration data we will reuse across tests
        self.valid_register_data = {
            'email': 'test@hospital.com',
            'password': 'Password123',
            'hospital_name': 'Test Hospital',
            'hospital_address': '123 Test Street',
            'hospital_tier': 'primary'
        }

    # --- REGISTRATION TESTS ---

    def test_register_success(self):
        """
        A hospital can register with valid data.
        Should return 201 with tokens and hospital info.
        """
        response = self.client.post(
            self.register_url,
            self.valid_register_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('hospital', response.data)
        self.assertEqual(response.data['user']['role'], 'hospital_admin')

    def test_register_creates_user_and_hospital(self):
        """
        Registration should create both a User and Hospital record.
        """
        self.client.post(
            self.register_url,
            self.valid_register_data,
            format='json'
        )
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Hospital.objects.count(), 1)

    def test_register_duplicate_email(self):
        """
        Cannot register with an email that already exists.
        Should return 400.
        """
        # Register once
        self.client.post(
            self.register_url,
            self.valid_register_data,
            format='json'
        )

        # Try to register again with same email
        response = self.client.post(
            self.register_url,
            self.valid_register_data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        """
        Registration should fail if required fields are missing.
        """
        response = self.client.post(
            self.register_url,
            {'email': 'test@hospital.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_email(self):
        """
        Registration should fail with an invalid email format.
        """
        data = self.valid_register_data.copy()
        data['email'] = 'notanemail'
        response = self.client.post(
            self.register_url,
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_tier(self):
        """
        Registration should fail with an invalid hospital tier.
        """
        data = self.valid_register_data.copy()
        data['hospital_tier'] = 'invalid_tier'
        response = self.client.post(
            self.register_url,
            data,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- LOGIN TESTS ---

    def test_login_success(self):
        """
        A registered user can log in with correct credentials.
        Should return 200 with tokens.
        """
        # Register first
        self.client.post(
            self.register_url,
            self.valid_register_data,
            format='json'
        )

        # Then login
        response = self.client.post(
            self.login_url,
            {
                'email': 'test@hospital.com',
                'password': 'Password123'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)

    def test_login_wrong_password(self):
        """
        Login should fail with wrong password.
        Should return 401.
        """
        self.client.post(
            self.register_url,
            self.valid_register_data,
            format='json'
        )

        response = self.client.post(
            self.login_url,
            {
                'email': 'test@hospital.com',
                'password': 'WrongPassword123'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_email(self):
        """
        Login should fail if email does not exist.
        Should return 401.
        """
        response = self.client.post(
            self.login_url,
            {
                'email': 'nobody@hospital.com',
                'password': 'Password123'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields(self):
        """
        Login should fail if email or password is missing.
        """
        response = self.client.post(
            self.login_url,
            {'email': 'test@hospital.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)