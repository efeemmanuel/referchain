from django.urls import path
from referrals.views import (
    ReferralAcceptView,
    ReferralChainView,
    ReferralCompleteView,
    ReferralDetailView,
    ReferralListView,
    ReferralRejectView,
)

urlpatterns = [
    path('', ReferralListView.as_view(), name='referral-list'),
    path('<int:referral_id>/', ReferralDetailView.as_view(), name='referral-detail'),
    path('<int:referral_id>/accept/', ReferralAcceptView.as_view(), name='referral-accept'),
    path('<int:referral_id>/reject/', ReferralRejectView.as_view(), name='referral-reject'),
    path('<int:referral_id>/complete/', ReferralCompleteView.as_view(), name='referral-complete'),
    path('<int:referral_id>/chain/', ReferralChainView.as_view(), name='referral-chain'),
]