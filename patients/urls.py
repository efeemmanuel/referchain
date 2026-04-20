from django.urls import path
from patients.views import (
    PatientListView,
    PatientDetailView,
    PatientCodeLookupView,
    MedicalRecordListView,
    MedicalRecordDetailView,
)

urlpatterns = [
    path('', PatientListView.as_view(), name='patient-list'),
    path('code/<str:code>/', PatientCodeLookupView.as_view(), name='patient-code-lookup'),
    path('<int:patient_id>/', PatientDetailView.as_view(), name='patient-detail'),
    path('<int:patient_id>/records/', MedicalRecordListView.as_view(), name='medical-record-list'),
    path('<int:patient_id>/records/<int:record_id>/', MedicalRecordDetailView.as_view(), name='medical-record-detail'),
]