from django.urls import path
from doctors.views import DoctorDetailView, DoctorListView

urlpatterns = [
    # /doctors/ — list all doctors
    path('', DoctorListView.as_view(), name='doctor-list'),

    # /doctors/{id}/ — get, update, delete a single doctor
    path('<int:doctor_id>/', DoctorDetailView.as_view(), name='doctor-detail'),
]