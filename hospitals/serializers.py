from rest_framework import serializers
from hospitals.models import Hospital


class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = [
            'id',
            'name',
            'address',
            'tier',
            'is_active',
            'is_verified',
            'created_at'
        ]
        read_only_fields = ['is_verified', 'created_at']