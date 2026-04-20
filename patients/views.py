from django.shortcuts import render
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from patients.models import Patient
from patients.permissions import IsHospitalAdminOrDoctor
from patients.serializers import PatientSerializer
from patients.utils import generate_qr_code, generate_unique_code


class PatientListView(APIView):
    """
    GET  /patients/ — list patients
    POST /patients/ — create a patient

    Hospital admin sees all patients in their hospital.
    Doctor sees only patients assigned to them.
    """
    permission_classes = [IsHospitalAdminOrDoctor]

    def get(self, request):
        # Hospital admin sees all patients in their hospital
        if request.user.role == User.Role.HOSPITAL_ADMIN:
            patients = Patient.objects.filter(
                hospital=request.user.hospital
            )
        else:
            # Doctor sees only their own patients
            patients = Patient.objects.filter(
                doctor=request.user.doctor
            )

        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PatientSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate unique code for this patient
        unique_code = generate_unique_code()

        # Generate QR code from the unique code
        qr_file = generate_qr_code(
            data=unique_code,
            filename=f'patient_{unique_code}.png'
        )

        # Determine the hospital based on who is creating the patient
        if request.user.role == User.Role.HOSPITAL_ADMIN:
            hospital = request.user.hospital
        else:
            # Doctor's hospital
            hospital = request.user.doctor.hospital

        # Save the patient
        patient = serializer.save(
            hospital=hospital,
            unique_code=unique_code,
        )

        # Save the QR code to the patient record
        patient.qr_code.save(qr_file.name, qr_file, save=True)

        return Response(
            PatientSerializer(patient).data,
            status=status.HTTP_201_CREATED
        )


class PatientDetailView(APIView):
    """
    GET    /patients/{id}/ — get a single patient by id
    PATCH  /patients/{id}/ — update a patient
    DELETE /patients/{id}/ — delete a patient
    """
    permission_classes = [IsHospitalAdminOrDoctor]

    def get_patient(self, patient_id, request):
        """
        Fetches a patient and checks access rights.

        Hospital admin can access any patient in their hospital.
        Doctor can only access their own patients.
        Receiving hospital can access a patient if they are
        an active recipient in that patient's referral chain.
        """
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return None, Response(
                {'error': 'Patient not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Hospital admin — must be same hospital
        if request.user.role == User.Role.HOSPITAL_ADMIN:
            if patient.hospital != request.user.hospital:
                # Check if this hospital is an active recipient
                # in this patient's referral chain
                is_active_recipient = patient.referrals.filter(
                    receiving_hospital=request.user.hospital,
                    status__in=['pending', 'accepted']
                ).exists()

                if not is_active_recipient:
                    return None, Response(
                        {'error': 'You do not have permission to access this patient.'},
                        status=status.HTTP_403_FORBIDDEN
                    )

        # Doctor — must be assigned to this patient
        elif request.user.role == User.Role.DOCTOR:
            if patient.doctor != request.user.doctor:
                return None, Response(
                    {'error': 'You do not have permission to access this patient.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        return patient, None

    def get(self, request, patient_id):
        patient, error = self.get_patient(patient_id, request)
        if error:
            return error

        # Check cache first before hitting the database
        cache_key = f'patient_{patient_id}'
        cached_data = cache.get(cache_key)

        if cached_data:
            # Return cached data directly — no database query needed
            return Response(cached_data, status=status.HTTP_200_OK)

        # Not in cache — query database and cache the result
        serializer = PatientSerializer(patient)
        cache.set(cache_key, serializer.data, settings.CACHE_TTL)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, patient_id):
        patient, error = self.get_patient(patient_id, request)
        if error:
            return error

        serializer = PatientSerializer(
            patient,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            # Invalidate cache when patient is updated
            # so the next GET returns fresh data
            cache.delete(f'patient_{patient_id}')

            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, patient_id):
        patient, error = self.get_patient(patient_id, request)
        if error:
            return error

        # Only hospital admin can delete a patient
        if request.user.role != User.Role.HOSPITAL_ADMIN:
            return Response(
                {'error': 'Only hospital admins can delete patients.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Block deletion if patient has active referrals
        active_referrals = patient.referrals.filter(
            status__in=['pending', 'accepted']
        ).exists()

        if active_referrals:
            return Response(
                {'error': 'This patient has active referrals and cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Invalidate cache on delete
        cache.delete(f'patient_{patient_id}')

        patient.delete()
        return Response(
            {'message': 'Patient deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )


class PatientCodeLookupView(APIView):
    """
    GET /patients/code/{code}/ — look up a patient by their unique code.

    Used when a patient arrives at a hospital and gives their code
    or the doctor scans their QR code.

    Both hospital admins and doctors can use this endpoint.
    Access is granted if the requesting user's hospital is either:
    - The hospital that created the patient
    - An active recipient in the patient's referral chain
    """
    permission_classes = [IsHospitalAdminOrDoctor]

    def get(self, request, code):
        # Look up patient by unique code
        try:
            patient = Patient.objects.get(unique_code=code)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'No patient found with this code.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Determine requesting user's hospital
        if request.user.role == User.Role.HOSPITAL_ADMIN:
            user_hospital = request.user.hospital
        else:
            user_hospital = request.user.doctor.hospital

        # Check if user's hospital has rights to view this patient
        is_original_hospital = patient.hospital == user_hospital
        is_active_recipient = patient.referrals.filter(
            receiving_hospital=user_hospital,
            status__in=['pending', 'accepted']
        ).exists()

        if not is_original_hospital and not is_active_recipient:
            return Response(
                {'error': 'You do not have permission to access this patient.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PatientSerializer(patient)
        return Response(serializer.data, status=status.HTTP_200_OK)
    



from patients.models import Patient, MedicalRecord
from patients.serializers import PatientSerializer, MedicalRecordSerializer


class MedicalRecordListView(APIView):
    """
    GET  /patients/{id}/records/ — list all records for a patient
    POST /patients/{id}/records/ — add a new record

    Both hospital admins and doctors can add records.
    Only the hospital that owns the patient or is an active
    recipient in the referral chain can access records.
    """
    permission_classes = [IsHospitalAdminOrDoctor]

    def get_patient(self, patient_id, request):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return None, Response(
                {'error': 'Patient not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.user.role == User.Role.HOSPITAL_ADMIN:
            if patient.hospital != request.user.hospital:
                is_active_recipient = patient.referrals.filter(
                    receiving_hospital=request.user.hospital,
                    status__in=['pending', 'accepted']
                ).exists()
                if not is_active_recipient:
                    return None, Response(
                        {'error': 'You do not have permission to access this patient.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
        elif request.user.role == User.Role.DOCTOR:
            if patient.doctor != request.user.doctor:
                return None, Response(
                    {'error': 'You do not have permission to access this patient.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        return patient, None

    def get(self, request, patient_id):
        patient, error = self.get_patient(patient_id, request)
        if error:
            return error

        records = patient.medical_records.all()
        serializer = MedicalRecordSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, patient_id):
        patient, error = self.get_patient(patient_id, request)
        if error:
            return error

        serializer = MedicalRecordSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set created_by to the logged in doctor
        # If hospital admin is creating, created_by is null
        created_by = None
        if request.user.role == User.Role.DOCTOR:
            created_by = request.user.doctor

        record = serializer.save(
            patient=patient,
            created_by=created_by
        )

        # Invalidate patient cache since records changed
        from django.core.cache import cache
        cache.delete(f'patient_{patient_id}')

        return Response(
            MedicalRecordSerializer(record).data,
            status=status.HTTP_201_CREATED
        )


class MedicalRecordDetailView(APIView):
    """
    DELETE /patients/{id}/records/{record_id}/ — delete a record

    Only the doctor who created the record or the hospital
    admin can delete it.
    """
    permission_classes = [IsHospitalAdminOrDoctor]

    def delete(self, request, patient_id, record_id):
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            record = MedicalRecord.objects.get(
                id=record_id,
                patient=patient
            )
        except MedicalRecord.DoesNotExist:
            return Response(
                {'error': 'Record not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Only the creating doctor or hospital admin can delete
        if request.user.role == User.Role.DOCTOR:
            if record.created_by != request.user.doctor:
                return Response(
                    {'error': 'You can only delete records you created.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        record.delete()

        # Invalidate patient cache
        from django.core.cache import cache
        cache.delete(f'patient_{patient_id}')

        return Response(
            {'message': 'Record deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )