from rest_framework.permissions import BasePermission


class IsHospitalAdmin(BasePermission):
    """
    Allows access only to users with the hospital_admin role.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'hospital_admin'
        )