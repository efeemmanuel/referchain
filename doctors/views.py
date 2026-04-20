from django.shortcuts import render

# Create your views here.
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from doctors.models import Doctor
from doctors.serializers import DoctorSerializer
from hospitals.permissions import IsHospitalAdmin
from referrals.models import Referral


class DoctorListView(APIView):
    """
    GET /doctors/ — list all doctors in the requesting admin's hospital.

    Only returns doctors belonging to the same hospital as the logged in admin.
    Never returns doctors from other hospitals.
    """
    permission_classes = [IsHospitalAdmin]

    def get(self, request):
        # Filter doctors by the admin's hospital only
        # This ensures hospital A can never see hospital B's doctors
        doctors = Doctor.objects.filter(
            hospital=request.user.hospital
        )

        # Empty list is valid — return 200 with empty array, not 404
        serializer = DoctorSerializer(doctors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DoctorDetailView(APIView):
    """
    GET    /doctors/{id}/ — retrieve a single doctor
    PATCH  /doctors/{id}/ — update a doctor
    DELETE /doctors/{id}/ — delete a doctor

    All actions are scoped to the admin's hospital.
    An admin cannot access, update, or delete doctors from other hospitals.
    """
    permission_classes = [IsHospitalAdmin]

    def get_doctor(self, doctor_id, hospital):
        """
        Helper method to fetch a doctor by id.
        Returns the doctor only if they belong to the requesting admin's hospital.

        We call this in get, patch, and delete instead of repeating
        the same query and checks three times.
        """
        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            # Doctor id does not exist at all
            return None, Response(
                {'error': 'Doctor not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Doctor exists but belongs to a different hospital
        # Return 403 so the admin knows they are not allowed
        # not 404, because 404 would hide that the doctor exists
        if doctor.hospital != hospital:
            return None, Response(
                {'error': 'You do not have permission to access this doctor.'},
                status=status.HTTP_403_FORBIDDEN
            )

        return doctor, None

    def get(self, request, doctor_id):
        doctor, error = self.get_doctor(doctor_id, request.user.hospital)

        # If get_doctor returned an error response, return it immediately
        if error:
            return error

        serializer = DoctorSerializer(doctor)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, doctor_id):
        doctor, error = self.get_doctor(doctor_id, request.user.hospital)

        if error:
            return error

        # partial=True means only the fields sent will be updated
        # Fields not sent will keep their current values
        serializer = DoctorSerializer(
            doctor,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, doctor_id):
        doctor, error = self.get_doctor(doctor_id, request.user.hospital)

        if error:
            return error

        # Block deletion if doctor has active referrals
        # Active means pending or accepted — not completed or rejected
        active_referrals = Referral.objects.filter(
            referring_doctor=doctor,
            status__in=[
                Referral.Status.PENDING,
                Referral.Status.ACCEPTED
            ]
        ).exists()

        if active_referrals:
            return Response(
                {'error': 'This doctor has active referrals and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Deleting the User record cascades and deletes the Doctor record too
        # because Doctor has CASCADE on the user OneToOneField
        doctor.user.delete()
        return Response(
            {'message': 'Doctor deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )