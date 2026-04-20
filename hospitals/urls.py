from django.urls import path
from hospitals.views import HospitalMeView, HospitalListView
from invitations.views import SendInviteView

urlpatterns = [
    path('', HospitalListView.as_view(), name='hospital-list'),
    path('me/', HospitalMeView.as_view(), name='hospital-me'),
    path('invite/', SendInviteView.as_view(), name='send-invite'),
]