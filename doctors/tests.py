from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from hospitals.models import Hospital
from doctors.models import Doctor


class DoctorTests(TestCase):
    """
    Tests for doctor endpoints.
    GET    /doctors/
    GET    /doctors/{id}/
    PATCH  /doctors/{id}/
    DELETE /doctors/{id}/
    """

    def setUp(self):
        self.client = APIClient()

        # Create hospital admin
        self.admin_user = User.objects.create_user(
            email='admin@hospital.com',
            password='Password123',
            role=User.Role.HOSPITAL_ADMIN
        )
        self.hospital = Hospital.objects.create(
            user=self.admin_user,
            name='Test Hospital',
            address='123 Test Street',
            tier=Hospital.Tier.PRIMARY
        )

        # Create a doctor
        self.doctor_user = User.objects.create_user(
            email='doctor@hospital.com',
            password='Password123',
            role=User.Role.DOCTOR
        )
        self.doctor = Doctor.objects.create(
            user=self.doctor_user,
            hospital=self.hospital,
            name='Dr. Emeka',
            specialty='Cardiology'
        )

        self.client.force_authenticate(user=self.admin_user)
        self.list_url = reverse('doctor-list')
        self.detail_url = reverse('doctor-detail', args=[self.doctor.id])

    def test_list_doctors_success(self):
        """
        Hospital admin can list all doctors in their hospital.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_doctors_empty(self):
        """
        Returns empty list if no doctors exist.
        """
        Doctor.objects.all().delete()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_get_doctor_success(self):
        """
        Hospital admin can get a single doctor by id.
        """
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Dr. Emeka')

    def test_get_doctor_not_found(self):
        """
        Returns 404 if doctor does not exist.
        """
        url = reverse('doctor-detail', args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_doctor_success(self):
        """
        Hospital admin can update a doctor's specialty.
        """
        response = self.client.patch(
            self.detail_url,
            {'specialty': 'Neurology'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['specialty'], 'Neurology')

    def test_delete_doctor_success(self):
        """
        Hospital admin can delete a doctor with no active referrals.
        """
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Doctor.objects.count(), 0)

    def test_doctor_cannot_access_doctor_endpoints(self):
        """
        A doctor cannot access doctor management endpoints.
        """
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)