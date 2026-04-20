from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from hospitals.models import Hospital
from doctors.models import Doctor
from patients.models import Patient
from referrals.models import Referral


class ReferralTests(TestCase):
    """
    Tests for referral endpoints.
    POST   /referrals/
    GET    /referrals/
    GET    /referrals/{id}/
    PATCH  /referrals/{id}/accept/
    PATCH  /referrals/{id}/reject/
    GET    /referrals/{id}/chain/
    """

    def setUp(self):
        self.client = APIClient()

        # Referring hospital
        self.admin_user = User.objects.create_user(
            email='admin@hospital.com',
            password='Password123',
            role=User.Role.HOSPITAL_ADMIN
        )
        self.hospital = Hospital.objects.create(
            user=self.admin_user,
            name='Referring Hospital',
            address='123 Test Street',
            tier=Hospital.Tier.PRIMARY
        )

        # Receiving hospital
        self.receiving_admin_user = User.objects.create_user(
            email='admin@receiving.com',
            password='Password123',
            role=User.Role.HOSPITAL_ADMIN
        )
        self.receiving_hospital = Hospital.objects.create(
            user=self.receiving_admin_user,
            name='Receiving Hospital',
            address='456 Receive Street',
            tier=Hospital.Tier.SECONDARY
        )

        # Doctor at referring hospital
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

        # Patient assigned to doctor
        self.patient = Patient.objects.create(
            hospital=self.hospital,
            doctor=self.doctor,
            name='John Doe',
            phone='08012345678',
            unique_code='TESTCODE'
        )

        # Create a referral — used for get, accept, reject, chain tests
        self.referral = Referral.objects.create(
            patient=self.patient,
            referring_doctor=self.doctor,
            referring_hospital=self.hospital,
            receiving_hospital=self.receiving_hospital,
            urgency_level=Referral.UrgencyLevel.HIGH,
            symptoms='Chest pain',
            status=Referral.Status.PENDING
        )

        self.list_url = reverse('referral-list')
        self.detail_url = reverse('referral-detail', args=[self.referral.id])
        self.accept_url = reverse('referral-accept', args=[self.referral.id])
        self.reject_url = reverse('referral-reject', args=[self.referral.id])
        self.chain_url = reverse('referral-chain', args=[self.referral.id])

    def test_create_referral_success(self):
        """
        Doctor can create a referral for their patient.
        Uses a fresh patient with no existing referrals.
        """
        # Create a fresh patient with no existing referrals
        fresh_patient = Patient.objects.create(
            hospital=self.hospital,
            doctor=self.doctor,
            name='Fresh Patient',
            phone='08099999999',
            unique_code='FRESHCODE'
        )

        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.post(
            self.list_url,
            {
                'patient': fresh_patient.id,
                'receiving_hospital': self.receiving_hospital.id,
                'urgency_level': 'high',
                'symptoms': 'Severe chest pain'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_cannot_create_referral(self):
        """
        Hospital admin cannot create referrals. Only doctors can.
        """
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            self.list_url,
            {
                'patient': self.patient.id,
                'receiving_hospital': self.receiving_hospital.id,
                'urgency_level': 'high',
                'symptoms': 'Chest pain'
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_referral_success(self):
        """
        Doctor can retrieve a referral they created.
        """
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'pending')

    def test_accept_referral_success(self):
        """
        Receiving hospital admin can accept a pending referral.
        Unique code and QR code should be generated.
        """
        self.client.force_authenticate(user=self.receiving_admin_user)
        response = self.client.patch(self.accept_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'accepted')
        self.assertIsNotNone(response.data['unique_code'])

    def test_reject_referral_success(self):
        """
        Receiving hospital admin can reject a pending referral.
        """
        self.client.force_authenticate(user=self.receiving_admin_user)
        response = self.client.patch(self.reject_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'rejected')

    def test_cannot_accept_already_accepted_referral(self):
        """
        Cannot accept a referral that is already accepted.
        """
        self.referral.status = Referral.Status.ACCEPTED
        self.referral.save()

        self.client.force_authenticate(user=self.receiving_admin_user)
        response = self.client.patch(self.accept_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_referring_hospital_cannot_accept(self):
        """
        The referring hospital cannot accept their own referral.
        Only the receiving hospital can.
        """
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(self.accept_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_referral_chain(self):
        """
        Can retrieve the full referral chain for a patient.
        Returns all referrals for that patient in order.
        """
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get(self.chain_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('chain', response.data)
        self.assertEqual(response.data['total_referrals'], 1)