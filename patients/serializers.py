from rest_framework import serializers
from patients.models import Patient, MedicalRecord


class MedicalRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for medical records.
    created_by_name pulls the doctor's name for display.
    created_by is read only — set automatically from logged in doctor.
    """
    created_by_name = serializers.CharField(
        source='created_by.name',
        read_only=True
    )

    class Meta:
        model = MedicalRecord
        fields = [
            'id',
            'record_type',
            'title',
            'content',
            'created_by',
            'created_by_name',
            'created_at',
        ]
        read_only_fields = ['created_by', 'created_at']


class PatientSerializer(serializers.ModelSerializer):
    """
    Serializer for the Patient model.
    Includes nested medical records so the full patient
    history is always available in one request.
    """
    medical_records = MedicalRecordSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id',
            'name',
            'phone',
            'email',
            'address',
            'unique_code',
            'qr_code',
            'hospital',
            'doctor',
            'medical_records',
            'created_at',
        ]
        read_only_fields = [
            'unique_code',
            'qr_code',
            'hospital',
            'medical_records',
            'created_at',
        ]

    def validate_phone(self, value):
        import re
        if not re.match(r'^\+?[0-9]{7,15}$', value):
            raise serializers.ValidationError(
                'Enter a valid phone number between 7 and 15 digits.'
            )
        return value

    def validate_name(self, value):
        import re
        if not re.match(r'^[a-zA-Z\s]+$', value):
            raise serializers.ValidationError(
                'Name can only contain letters and spaces.'
            )
        return value