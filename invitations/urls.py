from django.urls import path
from invitations.views import AcceptInvitationView, VerifyInvitationView

urlpatterns = [
    path('verify/', VerifyInvitationView.as_view(), name='invitation-verify'),
    path('accept/', AcceptInvitationView.as_view(), name='invitation-accept'),
]