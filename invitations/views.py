import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from doctors.models import Doctor
from hospitals.permissions import IsHospitalAdmin
from invitations.models import Invitation
from invitations.serializers import (
    AcceptInvitationSerializer,
    InvitationVerifySerializer,
    InviteSerializer,
)


class SendInviteView(APIView):
    """
    Hospital admin sends an invite to a doctor's email.

    POST /hospitals/invite/

    Success: 201 — invitation created and email sent
    Errors:
    - 400 — validation errors (duplicate invite, email already registered)
    - 401 — not authenticated
    - 403 — not a hospital admin
    - 500 — email sending failed
    """
    permission_classes = [IsHospitalAdmin]

    def post(self, request):
        serializer = InviteSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email']
        hospital = request.user.hospital

        # Generate a secure random token
        token = secrets.token_urlsafe(32)

        # Create the invitation record
        invitation = Invitation.objects.create(
            hospital=hospital,
            email=email,
            token=token,
            status=Invitation.Status.PENDING,
            expires_at=timezone.now() + timedelta(hours=48)
        )

        # Build the invite link
        invite_link = f"{settings.FRONTEND_URL}/invitations/accept?token={token}"

        # Send the email
        try:
            send_mail(
                subject='You have been invited to ReferChain',
                message=f"""
Hello,

You have been invited to join {hospital.name} on ReferChain.

Click the link below to complete your registration:
{invite_link}

This link expires in 48 hours.

ReferChain Team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception:
            # If email fails, delete the invitation and return an error
            # We do not want orphaned invitations with no email sent
            invitation.delete()
            return Response(
                {'error': 'Failed to send invitation email. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'message': f'Invitation sent successfully to {email}',
            'expires_at': invitation.expires_at
        }, status=status.HTTP_201_CREATED)


class VerifyInvitationView(APIView):
    """
    Doctor verifies their invite token before seeing the registration form.

    GET /invitations/verify/?token=<token>

    Success: 200 — token is valid, returns email and hospital name
    Errors:
    - 400 — token missing, invalid, expired, or already used
    """
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token')

        # Check token was provided in query params
        if not token:
            return Response(
                {'error': 'Token is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = InvitationVerifySerializer(data={'token': token})

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        invitation = Invitation.objects.get(token=token)

        return Response({
            'email': invitation.email,
            'hospital': invitation.hospital.name,
            'expires_at': invitation.expires_at
        }, status=status.HTTP_200_OK)


class AcceptInvitationView(APIView):
    """
    Doctor completes their profile and sets their password.

    POST /invitations/accept/

    Success: 201 — User + Doctor created, invitation marked accepted
    Errors:
    - 400 — validation errors, invalid token, expired token
    - 409 — email already registered
    """
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        token = serializer.validated_data['token']

        # Verify token is valid and pending
        try:
            invitation = Invitation.objects.get(
                token=token,
                status=Invitation.Status.PENDING
            )
        except Invitation.DoesNotExist:
            return Response(
                {'error': 'This invitation is invalid or has already been used.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check token has not expired
        if invitation.expires_at < timezone.now():
            invitation.status = Invitation.Status.EXPIRED
            invitation.save()
            return Response(
                {'error': 'This invitation has expired. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check email is not already registered
        # Using 409 Conflict because the resource (email) already exists
        if User.objects.filter(email=invitation.email).exists():
            return Response(
                {'error': 'A user with this email already exists.'},
                status=status.HTTP_409_CONFLICT
            )

        # Create User record for the doctor
        user = User.objects.create_user(
            email=invitation.email,
            password=serializer.validated_data['password'],
            role=User.Role.DOCTOR
        )

        # Create Doctor record
        Doctor.objects.create(
            user=user,
            hospital=invitation.hospital,
            name=serializer.validated_data['name'],
            specialty=serializer.validated_data['specialty'],
        )

        # Mark invitation as accepted
        invitation.status = Invitation.Status.ACCEPTED
        invitation.save()

        return Response({
            'message': 'Account created successfully. You can now log in.',
            'email': invitation.email,
            'hospital': invitation.hospital.name
        }, status=status.HTTP_201_CREATED)