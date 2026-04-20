from django.core import mail
from django.core import mail
from doctors.models import Doctor
from patients.models import Patient
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.core import mail
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from hospitals.models import Hospital
from doctors.models import Doctor
from patients.models import Patient
from invitations.models import Invitation
import secrets

class EmailNotificationTests(TestCase):
    """
    Tests that emails are sent correctly.
    Django's test runner automatically uses an in-memory email backend
    so no real emails are sent during tests.
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

        self.client.force_authenticate(user=self.admin_user)
        self.invite_url = reverse('send-invite')

    def test_invite_email_is_sent(self):
        """
        Sending an invite should trigger one email
        to the doctor's email address.
        """
        response = self.client.post(
            self.invite_url,
            {
                'email': 'doctor@example.com',
                'doctor_name': 'Dr. Emeka'
            },
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Django captures sent emails in mail.outbox during tests
        self.assertEqual(len(mail.outbox), 1)

    def test_invite_email_sent_to_correct_address(self):
        """
        The invite email should be sent to the doctor's email address.
        """
        self.client.post(
            self.invite_url,
            {
                'email': 'doctor@example.com',
                'doctor_name': 'Dr. Emeka'
            },
            format='json'
        )

        # Check the email was sent to the right address
        self.assertEqual(mail.outbox[0].to, ['doctor@example.com'])

    def test_invite_email_subject(self):
        """
        The invite email should have the correct subject line.
        """
        self.client.post(
            self.invite_url,
            {
                'email': 'doctor@example.com',
                'doctor_name': 'Dr. Emeka'
            },
            format='json'
        )

        self.assertEqual(
            mail.outbox[0].subject,
            'You have been invited to ReferChain'
        )

    def test_invite_email_contains_hospital_name(self):
        """
        The invite email body should mention the hospital name.
        """
        self.client.post(
            self.invite_url,
            {
                'email': 'doctor@example.com',
                'doctor_name': 'Dr. Emeka'
            },
            format='json'
        )

        self.assertIn('Test Hospital', mail.outbox[0].body)

    def test_invite_email_contains_invite_link(self):
        """
        The invite email body should contain the invite link with token.
        """
        self.client.post(
            self.invite_url,
            {
                'email': 'doctor@example.com',
                'doctor_name': 'Dr. Emeka'
            },
            format='json'
        )

        # Check the email body contains an invite link
        self.assertIn('invitations/accept?token=', mail.outbox[0].body)

    def test_no_email_sent_on_invalid_invite(self):
        """
        No email should be sent if the invite request is invalid.
        For example if the email is already registered.
        """
        # Register the email as an existing user first
        User.objects.create_user(
            email='existing@example.com',
            password='Password123',
            role=User.Role.DOCTOR
        )

        self.client.post(
            self.invite_url,
            {
                'email': 'existing@example.com',
                'doctor_name': 'Dr. Emeka'
            },
            format='json'
        )

        # No email should have been sent
        self.assertEqual(len(mail.outbox), 0)

    def test_referral_notification_email_is_sent(self):
        """
        Creating a referral should send a notification email
        to the receiving hospital.
        """
        # Create receiving hospital
        receiving_admin = User.objects.create_user(
            email='admin@receiving.com',
            password='Password123',
            role=User.Role.HOSPITAL_ADMIN
        )
        receiving_hospital = Hospital.objects.create(
            user=receiving_admin,
            name='Receiving Hospital',
            address='456 Receive Street',
            tier=Hospital.Tier.SECONDARY
        )

        # Create doctor
        doctor_user = User.objects.create_user(
            email='doctor@hospital.com',
            password='Password123',
            role=User.Role.DOCTOR
        )
        doctor = Doctor.objects.create(
            user=doctor_user,
            hospital=self.hospital,
            name='Dr. Emeka',
            specialty='Cardiology'
        )

        # Create patient
        patient = Patient.objects.create(
            hospital=self.hospital,
            doctor=doctor,
            name='John Doe',
            phone='08012345678',
            unique_code='TESTCODE'
        )

        # Create referral as doctor
        self.client.force_authenticate(user=doctor_user)
        self.client.post(
            reverse('referral-list'),
            {
                'patient': patient.id,
                'receiving_hospital': receiving_hospital.id,
                'urgency_level': 'high',
                'symptoms': 'Chest pain'
            },
            format='json'
        )

        # One email should have been sent to receiving hospital
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['admin@receiving.com'])

    def test_referral_email_contains_patient_name(self):
        """
        The referral notification email should mention the patient's name.
        """
        receiving_admin = User.objects.create_user(
            email='admin@receiving.com',
            password='Password123',
            role=User.Role.HOSPITAL_ADMIN
        )
        receiving_hospital = Hospital.objects.create(
            user=receiving_admin,
            name='Receiving Hospital',
            address='456 Receive Street',
            tier=Hospital.Tier.SECONDARY
        )

        doctor_user = User.objects.create_user(
            email='doctor@hospital.com',
            password='Password123',
            role=User.Role.DOCTOR
        )
        doctor = Doctor.objects.create(
            user=doctor_user,
            hospital=self.hospital,
            name='Dr. Emeka',
            specialty='Cardiology'
        )

        patient = Patient.objects.create(
            hospital=self.hospital,
            doctor=doctor,
            name='John Doe',
            phone='08012345678',
            unique_code='TESTCODE'
        )

        self.client.force_authenticate(user=doctor_user)
        self.client.post(
            reverse('referral-list'),
            {
                'patient': patient.id,
                'receiving_hospital': receiving_hospital.id,
                'urgency_level': 'high',
                'symptoms': 'Chest pain'
            },
            format='json'
        )

        # Patient name should appear in the email body
        self.assertIn('John Doe', mail.outbox[0].body)