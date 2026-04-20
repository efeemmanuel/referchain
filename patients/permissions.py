from rest_framework.permissions import BasePermission
from accounts.models import User


class IsHospitalAdminOrDoctor(BasePermission):
    """
    Allows access to both hospital_admin and doctor roles.
    Used for endpoints that both user types can access.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in [
                User.Role.HOSPITAL_ADMIN,
                User.Role.DOCTOR
            ]
        )