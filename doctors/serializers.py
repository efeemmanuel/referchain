from rest_framework import serializers
from doctors.models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    """
    Serializer for the Doctor model.
    Handles both reading and updating doctor records.

    read_only_fields — these fields are returned in responses
    but cannot be changed via PATCH or any other request.
    user and hospital are set at creation time and never change.
    """

    # Pull email from the related User model
    # so it shows up in the response without a nested object
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Doctor
        fields = [
            'id',
            'name',
            'email',
            'specialty',
            'is_active',
            'is_verified',
            'hospital',
            'created_at'
        ]
        read_only_fields = [
            'user',
            'hospital',
            'is_verified',
            'created_at'
        ]