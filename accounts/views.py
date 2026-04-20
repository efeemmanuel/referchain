# Create your views here.
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers import LoginSerializer, RegisterSerializer
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema


class RegisterView(APIView):
    """
    Public endpoint. No authentication required.
    Creates a hospital admin account + hospital record together.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Auth'],
        summary='Register a hospital',
        description='Creates a hospital admin account and hospital record together.'
    )

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user, hospital = serializer.save()

            # Generate JWT tokens for the new user
            refresh = RefreshToken.for_user(user)

            return Response({
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'role': user.role,
                },
                'hospital': {
                    'id': hospital.id,
                    'name': hospital.name,
                    'tier': hospital.tier,
                }
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    Public endpoint. No authentication required.
    Works for both hospital_admin and doctor.
    Returns JWT tokens + user info.
    """
    
    permission_classes = [AllowAny]


    @extend_schema(
        tags=['Auth'],
        summary='Login',
        description='Login for both hospital admins and doctors. Returns JWT tokens.'
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            # authenticate checks email + password against the database
            user = authenticate(request, email=email, password=password)

            if not user:
                return Response(
                    {'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not user.is_active:
                return Response(
                    {'error': 'Account is inactive'},
                    status=status.HTTP_403_FORBIDDEN
                )

            refresh = RefreshToken.for_user(user)

            return Response({
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'role': user.role,
                }
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)