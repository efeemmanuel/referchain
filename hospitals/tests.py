from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from hospitals.models import Hospital


class HospitalTests(TestCase):
    """
    Tests for hospital endpoints.
    GET /hospitals/me/
    PATCH /hospitals/me/
    DELETE /hospitals/me/
    """

    def setUp(self):
        """
        Creates a hospital admin user and authenticates the client.
        This runs before every test so each test starts fresh.
        """
        self.client = APIClient()

        # Create user
        self.user = User.objects.create_user(
            email='admin@hospital.com',
            password='Password123',
            role=User.Role.HOSPITAL_ADMIN
        )

        # Create hospital linked to user
        self.hospital = Hospital.objects.create(
            user=self.user,
            name='Test Hospital',
            address='123 Test Street',
            tier=Hospital.Tier.PRIMARY
        )

        # Authenticate the client with this user's token
        self.client.force_authenticate(user=self.user)

        self.me_url = reverse('hospital-me')

    def test_get_hospital_success(self):
        """
        Hospital admin can retrieve their hospital profile.
        """
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Hospital')

    def test_get_hospital_unauthenticated(self):
        """
        Unauthenticated request should return 401.
        """
        self.client.force_authenticate(user=None)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_hospital_success(self):
        """
        Hospital admin can update their hospital name and address.
        """
        response = self.client.patch(
            self.me_url,
            {'name': 'Updated Hospital Name'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Hospital Name')

    def test_patch_hospital_partial(self):
        """
        PATCH should only update fields that are sent.
        Other fields should remain unchanged.
        """
        response = self.client.patch(
            self.me_url,
            {'name': 'New Name'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Address should remain unchanged
        self.assertEqual(response.data['address'], '123 Test Street')

    def test_delete_hospital_success(self):
        """
        Hospital admin can delete their account.
        Should return 204 and remove both user and hospital.
        """
        response = self.client.delete(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Hospital.objects.count(), 0)

    def test_doctor_cannot_access_hospital_endpoints(self):
        """
        A doctor should not be able to access hospital endpoints.
        Should return 403.
        """
        doctor_user = User.objects.create_user(
            email='doctor@hospital.com',
            password='Password123',
            role=User.Role.DOCTOR
        )
        self.client.force_authenticate(user=doctor_user)
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)