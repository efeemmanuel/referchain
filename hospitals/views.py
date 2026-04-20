from django.shortcuts import render

# Create your views here.
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from hospitals.permissions import IsHospitalAdmin
from hospitals.serializers import HospitalSerializer
from drf_spectacular.utils import extend_schema



class HospitalMeView(APIView):
    """
    GET    /hospitals/me  — retrieve my hospital profile
    PATCH  /hospitals/me  — update my hospital profile
    DELETE /hospitals/me  — delete my hospital account
    """
    permission_classes = [IsHospitalAdmin]

    def get_hospital(self, request):
        """
        Helper method to get the hospital belonging to the current user.
        We use this in every method below instead of repeating the query.
        """
        try:
            return request.user.hospital
        except Exception:
            return None

    @extend_schema(tags=['Hospitals'], summary='Get my hospital profile')
    def get(self, request):
        hospital = self.get_hospital(request)

        if not hospital:
            return Response(
                {'error': 'Hospital not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = HospitalSerializer(hospital)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(tags=['Hospitals'], summary='Update my hospital profile')
    def patch(self, request):
        hospital = self.get_hospital(request)

        if not hospital:
            return Response(
                {'error': 'Hospital not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # partial=True means only the fields sent will be updated.
        # Without partial=True all fields would be required.
        serializer = HospitalSerializer(hospital, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(tags=['Hospitals'], summary='Delete my hospital account')
    def delete(self, request):
        hospital = self.get_hospital(request)

        if not hospital:
            return Response(
                {'error': 'Hospital not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Deleting the user cascades and deletes the hospital too
        # because Hospital has CASCADE on the user ForeignKey
        request.user.delete()
        return Response(
            {'message': 'Account deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )
    




from rest_framework.permissions import IsAuthenticated
from hospitals.models import Hospital
from hospitals.serializers import HospitalSerializer


class HospitalListView(APIView):
    """
    GET /hospitals/ — list all hospitals in the system.
    Used when creating a referral to search for receiving hospital.
    Excludes the requesting user's own hospital.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get all active hospitals except the user's own hospital
        hospitals = Hospital.objects.filter(is_active=True)

        # Exclude own hospital so doctors can't refer to themselves
        try:
            if request.user.role == 'hospital_admin':
                own_hospital = request.user.hospital
            else:
                own_hospital = request.user.doctor.hospital
            hospitals = hospitals.exclude(id=own_hospital.id)
        except Exception:
            pass

        serializer = HospitalSerializer(hospitals, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    






