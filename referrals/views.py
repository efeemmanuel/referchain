from django.core.cache import cache
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from hospitals.permissions import IsHospitalAdmin
from patients.permissions import IsHospitalAdminOrDoctor
from referrals.models import Referral
from referrals.serializers import CreateReferralSerializer, ReferralSerializer
from referrals.utils import generate_referral_code, generate_referral_qr


class IsDoctor(IsAuthenticated):
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view) and
            request.user.role == User.Role.DOCTOR
        )


class ReferralListView(APIView):
    """
    GET  /referrals/ — list referrals
    POST /referrals/ — create a referral
    """
    permission_classes = [IsHospitalAdminOrDoctor]

    def get(self, request):
        if request.user.role == User.Role.HOSPITAL_ADMIN:
            hospital = request.user.hospital
            referrals = Referral.objects.filter(
                referring_hospital=hospital
            ) | Referral.objects.filter(
                receiving_hospital=hospital
            )
            referrals = referrals.distinct().order_by('-created_at')
        else:
            referrals = Referral.objects.filter(
                referring_doctor=request.user.doctor
            ).order_by('-created_at')

        serializer = ReferralSerializer(referrals, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if request.user.role != User.Role.DOCTOR:
            return Response(
                {'error': 'Only doctors can create referrals.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = CreateReferralSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        doctor = request.user.doctor

        referral = Referral.objects.create(
            patient=serializer.validated_data['patient'],
            referring_doctor=doctor,
            referring_hospital=doctor.hospital,
            receiving_hospital=serializer.validated_data['receiving_hospital'],
            receiving_doctor=serializer.validated_data.get('receiving_doctor'),
            urgency_level=serializer.validated_data['urgency_level'],
            symptoms=serializer.validated_data['symptoms'],
            test_attachments=serializer.validated_data.get('test_attachments', []),
            status=Referral.Status.PENDING
        )

        return Response(
            ReferralSerializer(referral).data,
            status=status.HTTP_201_CREATED
        )


class ReferralDetailView(APIView):
    """
    GET /referrals/{id}/ — get a single referral
    """
    permission_classes = [IsHospitalAdminOrDoctor]

    def get_referral(self, referral_id, request):
        try:
            referral = Referral.objects.get(id=referral_id)
        except Referral.DoesNotExist:
            return None, Response(
                {'error': 'Referral not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.user.role == User.Role.HOSPITAL_ADMIN:
            hospital = request.user.hospital
            has_access = (
                referral.referring_hospital == hospital or
                referral.receiving_hospital == hospital
            )
        else:
            has_access = referral.referring_doctor == request.user.doctor

        if not has_access:
            return None, Response(
                {'error': 'You do not have permission to access this referral.'},
                status=status.HTTP_403_FORBIDDEN
            )

        return referral, None

    def get(self, request, referral_id):
        referral, error = self.get_referral(referral_id, request)
        if error:
            return error

        cache_key = f'referral_{referral_id}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        serializer = ReferralSerializer(referral)
        cache.set(cache_key, serializer.data, settings.CACHE_TTL)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReferralAcceptView(APIView):
    """
    PATCH /referrals/{id}/accept/ — accept a referral

    Order matters here:
    1. Save unique code first
    2. Save QR code second
    3. Set status to accepted and save last
    Signal fires on step 3 — QR already exists so patient email works
    """
    permission_classes = [IsHospitalAdmin]

    def patch(self, request, referral_id):
        try:
            referral = Referral.objects.get(id=referral_id)
        except Referral.DoesNotExist:
            return Response(
                {'error': 'Referral not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if referral.receiving_hospital != request.user.hospital:
            return Response(
                {'error': 'Only the receiving hospital can accept this referral.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if referral.status != Referral.Status.PENDING:
            return Response(
                {'error': f'Cannot accept a referral with status: {referral.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        unique_code = generate_referral_code()
        qr_file = generate_referral_qr(
            data=unique_code,
            filename=f'referral_{unique_code}.png'
        )

        # Step 1 — save unique code
        referral.unique_code = unique_code
        referral.save(update_fields=['unique_code'])

        # Step 2 — save QR code without triggering save yet
        referral.qr_code.save(qr_file.name, qr_file, save=False)

        # Step 3 — set accepted and save — signal fires here with QR already attached
        referral.status = Referral.Status.ACCEPTED
        referral.save()

        cache.delete(f'referral_{referral_id}')
        cache.delete(f'referral_chain_{referral_id}')

        return Response(
            ReferralSerializer(referral).data,
            status=status.HTTP_200_OK
        )


class ReferralRejectView(APIView):
    """
    PATCH /referrals/{id}/reject/ — reject a referral
    """
    permission_classes = [IsHospitalAdmin]

    def patch(self, request, referral_id):
        try:
            referral = Referral.objects.get(id=referral_id)
        except Referral.DoesNotExist:
            return Response(
                {'error': 'Referral not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if referral.receiving_hospital != request.user.hospital:
            return Response(
                {'error': 'Only the receiving hospital can reject this referral.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if referral.status != Referral.Status.PENDING:
            return Response(
                {'error': f'Cannot reject a referral with status: {referral.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        referral.status = Referral.Status.REJECTED
        referral.save()

        cache.delete(f'referral_{referral_id}')
        cache.delete(f'referral_chain_{referral_id}')

        return Response(
            ReferralSerializer(referral).data,
            status=status.HTTP_200_OK
        )


class ReferralChainView(APIView):
    """
    GET /referrals/{id}/chain/ — get full referral chain for a patient
    """
    permission_classes = [IsHospitalAdminOrDoctor]

    def get(self, request, referral_id):
        try:
            referral = Referral.objects.get(id=referral_id)
        except Referral.DoesNotExist:
            return Response(
                {'error': 'Referral not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.user.role == User.Role.HOSPITAL_ADMIN:
            hospital = request.user.hospital
            has_access = (
                referral.referring_hospital == hospital or
                referral.receiving_hospital == hospital
            )
        else:
            has_access = referral.referring_doctor == request.user.doctor

        if not has_access:
            return Response(
                {'error': 'You do not have permission to view this referral chain.'},
                status=status.HTTP_403_FORBIDDEN
            )

        cache_key = f'referral_chain_{referral_id}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        chain = Referral.objects.filter(
            patient=referral.patient
        ).order_by('created_at')

        serializer = ReferralSerializer(chain, many=True)

        response_data = {
            'patient': referral.patient.name,
            'total_referrals': chain.count(),
            'chain': serializer.data
        }

        cache.set(cache_key, response_data, settings.CACHE_TTL)
        return Response(response_data, status=status.HTTP_200_OK)
    






class ReferralCompleteView(APIView):
    """
    PATCH /referrals/{id}/complete/ — mark a referral as completed

    Only the receiving hospital admin can complete a referral.
    Only accepted referrals can be completed.
    Signals the patient's treatment at the receiving hospital is done.
    """
    permission_classes = [IsHospitalAdmin]

    def patch(self, request, referral_id):
        try:
            referral = Referral.objects.get(id=referral_id)
        except Referral.DoesNotExist:
            return Response(
                {'error': 'Referral not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Only the receiving hospital can complete
        if referral.receiving_hospital != request.user.hospital:
            return Response(
                {'error': 'Only the receiving hospital can complete this referral.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Can only complete an accepted referral
        if referral.status != Referral.Status.ACCEPTED:
            return Response(
                {'error': f'Cannot complete a referral with status: {referral.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        referral.status = Referral.Status.COMPLETED
        referral.save()

        # Invalidate cache
        cache.delete(f'referral_{referral_id}')
        cache.delete(f'referral_chain_{referral_id}')

        return Response(
            ReferralSerializer(referral).data,
            status=status.HTTP_200_OK
        )