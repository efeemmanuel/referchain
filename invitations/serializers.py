from django.utils import timezone
from rest_framework import serializers

from accounts.models import User
from invitations.models import Invitation


class InviteSerializer(serializers.Serializer):
    """
    Validates the invite request from a hospital admin.
    Edge cases handled:
    - Email already registered as a user in the system
    - Email already has a pending invite from this hospital
    - Email already has an accepted invite from this hospital (already a doctor here)
    """
    email = serializers.EmailField()
    doctor_name = serializers.CharField(max_length=255)

    def validate_email(self, value):
        hospital = self.context['request'].user.hospital

        # Check if this email already belongs to a user in the system
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'This email is already registered in the system.'
            )

        # Check if a pending invite already exists for this email at this hospital
        if Invitation.objects.filter(
            email=value,
            hospital=hospital,
            status=Invitation.Status.PENDING
        ).exists():
            raise serializers.ValidationError(
                'A pending invitation already exists for this email.'
            )

        # Check if this email was already accepted at this hospital
        if Invitation.objects.filter(
            email=value,
            hospital=hospital,
            status=Invitation.Status.ACCEPTED
        ).exists():
            raise serializers.ValidationError(
                'This email has already accepted an invitation to your hospital.'
            )

        return value


class InvitationVerifySerializer(serializers.Serializer):
    """
    Validates that the token exists, is pending, and has not expired.
    Edge cases handled:
    - Token does not exist
    - Token already accepted
    - Token already expired
    - Token just expired (catches tokens that expired but were not marked yet)
    """
    token = serializers.CharField()

    def validate_token(self, value):
        # Check token exists
        try:
            invitation = Invitation.objects.get(token=value)
        except Invitation.DoesNotExist:
            raise serializers.ValidationError(
                'This invitation link is invalid.'
            )

        # Check token was not already accepted
        if invitation.status == Invitation.Status.ACCEPTED:
            raise serializers.ValidationError(
                'This invitation has already been accepted.'
            )

        # Check token was not already marked expired
        if invitation.status == Invitation.Status.EXPIRED:
            raise serializers.ValidationError(
                'This invitation has expired. Please request a new one.'
            )

        # Check token has not just expired (but was not marked yet)
        if invitation.expires_at < timezone.now():
            invitation.status = Invitation.Status.EXPIRED
            invitation.save()
            raise serializers.ValidationError(
                'This invitation has expired. Please request a new one.'
            )

        return value


class AcceptInvitationSerializer(serializers.Serializer):
    """
    Validates the doctor's registration data when accepting an invite.
    Edge cases handled:
    - Password too short
    - Password missing uppercase letter
    - Password missing a number
    - Name contains numbers or special characters
    - Specialty contains numbers or special characters
    """
    token = serializers.CharField()
    name = serializers.CharField(max_length=255)
    specialty = serializers.CharField(max_length=255)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_name(self, value):
        # Name should only contain letters, spaces, and dots (for Dr. prefix)
        import re
        if not re.match(r"^[a-zA-Z\s.]+$", value):
            raise serializers.ValidationError(
                'Name can only contain letters, spaces, and dots.'
            )
        return value

    def validate_specialty(self, value):
        import re
        if not re.match(r"^[a-zA-Z\s]+$", value):
            raise serializers.ValidationError(
                'Specialty can only contain letters and spaces.'
            )
        return value

    def validate_password(self, value):
        # Must have at least one uppercase letter
        if not any(char.isupper() for char in value):
            raise serializers.ValidationError(
                'Password must contain at least one uppercase letter.'
            )
        # Must have at least one number
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError(
                'Password must contain at least one number.'
            )
        return value