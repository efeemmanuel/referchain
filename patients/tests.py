from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from hospitals.models import Hospital
from doctors.models import Doctor
from patients.models import Patient


class PatientTests(TestCase):
    """
    Tests for patient endpoints.
    POST   /patients/
    GET    /patients/
    GET    /patients/{id}/
    GET    /patients/code/{code}/
    PATCH  /patients/{id}/
    DELETE /patients/{id}/
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

        # Create doctor
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

        # Create a patient
        self.patient = Patient.objects.create(
            hospital=self.hospital,
            doctor=self.doctor,
            name='John Doe',
            phone='08012345678',
            unique_code='TESTCODE'
        )

        self.client.force_authenticate(user=self.admin_user)
        self.list_url = reverse('patient-list')
        self.detail_url = reverse('patient-detail', args=[self.patient.id])
        self.code_url = reverse('patient-code-lookup', args=['TESTCODE'])

    def test_create_patient_success(self):
        """
        Hospital admin can create a patient.
        Unique code and QR code are auto generated.
        """
        response = self.client.post(
            self.list_url,
            {
                'name': 'Jane Doe',
                'phone': '08098765432',
                'doctor': self.doctor.id
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('unique_code', response.data)
        self.assertIsNotNone(response.data['unique_code'])

    def test_list_patients_as_admin(self):
        """
        Hospital admin sees all patients in their hospital.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_patients_as_doctor(self):
        """
        Doctor only sees patients assigned to them.
        """
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_patient_by_id(self):
        """
        Can retrieve a patient by their id.
        """
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'John Doe')

    def test_get_patient_by_code(self):
        """
        Can retrieve a patient by their unique code.
        Used for QR scan lookup.
        """
        response = self.client.get(self.code_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unique_code'], 'TESTCODE')

    def test_get_patient_invalid_code(self):
        """
        Returns 404 for a code that does not exist.
        """
        url = reverse('patient-code-lookup', args=['INVALID'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_patient_success(self):
        """
        Can update a patient's phone number.
        """
        response = self.client.patch(
            self.detail_url,
            {'phone': '08011111111'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone'], '08011111111')

    def test_delete_patient_success(self):
        """
        Hospital admin can delete a patient with no active referrals.
        """
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Patient.objects.count(), 0)