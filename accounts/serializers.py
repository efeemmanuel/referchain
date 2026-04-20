from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from hospitals.models import Hospital


class RegisterSerializer(serializers.Serializer):
    # User fields
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    # Hospital fields
    hospital_name = serializers.CharField(max_length=255)
    hospital_address = serializers.CharField()
    hospital_tier = serializers.ChoiceField(choices=Hospital.Tier.choices)

    def validate_email(self, value):
        """Check that the email is not already registered."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        """
        Creates User and Hospital together in one atomic transaction.
        If either fails, both are rolled back. No orphaned records.
        """
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role=User.Role.HOSPITAL_ADMIN
        )

        hospital = Hospital.objects.create(
            user=user,
            name=validated_data['hospital_name'],
            address=validated_data['hospital_address'],
            tier=validated_data['hospital_tier']
        )

        return user, hospital


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True) 