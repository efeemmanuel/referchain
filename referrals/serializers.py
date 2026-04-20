from rest_framework import serializers
from referrals.models import Referral
from patients.models import Patient
from hospitals.models import Hospital
from doctors.models import Doctor


class ReferralSerializer(serializers.ModelSerializer):
    """
    Used for reading referral data.
    All relational fields are read only.
    Shows nested details for patient, hospitals, and doctors.
    """

    # Show patient name instead of just id
    patient_name = serializers.CharField(
        source='patient.name',
        read_only=True
    )

    # Show hospital names instead of just ids
    referring_hospital_name = serializers.CharField(
        source='referring_hospital.name',
        read_only=True
    )
    receiving_hospital_name = serializers.CharField(
        source='receiving_hospital.name',
        read_only=True
    )

    # Show doctor name instead of just id
    referring_doctor_name = serializers.CharField(
        source='referring_doctor.name',
        read_only=True
    )

    class Meta:
        model = Referral
        fields = [
            'id',
            'patient',
            'patient_name',
            'referring_doctor',
            'referring_doctor_name',
            'referring_hospital',
            'referring_hospital_name',
            'receiving_hospital',
            'receiving_hospital_name',
            'receiving_doctor',
            'urgency_level',
            'symptoms',
            'test_attachments',
            'status',
            'unique_code',
            'qr_code',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'referring_doctor',
            'referring_hospital',
            'status',
            'unique_code',
            'qr_code',
            'created_at',
            'updated_at'
        ]


class CreateReferralSerializer(serializers.Serializer):
    """
    Used only for creating a referral.
    Doctors send patient, receiving hospital, urgency, symptoms.
    referring_doctor and referring_hospital are set automatically
    from the logged in doctor — never sent by the user.
    """
    patient = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all()
    )
    receiving_hospital = serializers.PrimaryKeyRelatedField(
        queryset=Hospital.objects.all()
    )
    receiving_doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.all(),
        required=False,
        allow_null=True
    )
    urgency_level = serializers.ChoiceField(
        choices=Referral.UrgencyLevel.choices
    )
    symptoms = serializers.CharField()
    test_attachments = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )

    def validate(self, data):
        request = self.context['request']
        doctor = request.user.doctor

        # Doctor can only refer their own patients
        if data['patient'].doctor != doctor:
            raise serializers.ValidationError(
                'You can only refer patients assigned to you.'
            )

        # Cannot refer to your own hospital
        if data['receiving_hospital'] == doctor.hospital:
            raise serializers.ValidationError(
                'You cannot refer a patient to your own hospital.'
            )

        # Check patient does not already have a pending
        # referral to the same hospital
        already_referred = Referral.objects.filter(
            patient=data['patient'],
            receiving_hospital=data['receiving_hospital'],
            status=Referral.Status.PENDING
        ).exists()

        if already_referred:
            raise serializers.ValidationError(
                'This patient already has a pending referral to this hospital.'
            )

        # If receiving doctor is provided, make sure they
        # belong to the receiving hospital
        if data.get('receiving_doctor'):
            if data['receiving_doctor'].hospital != data['receiving_hospital']:
                raise serializers.ValidationError(
                    'The receiving doctor does not belong to the receiving hospital.'
                )

        return data