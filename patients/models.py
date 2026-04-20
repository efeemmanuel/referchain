from django.db import models


class Patient(models.Model):
    hospital = models.ForeignKey(
        'hospitals.Hospital',
        on_delete=models.CASCADE,
        related_name='patients'
    )
    doctor = models.ForeignKey(
        'doctors.Doctor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patients'
    )
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    unique_code = models.CharField(max_length=20, unique=True)
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class MedicalRecord(models.Model):
    class RecordType(models.TextChoices):
        SYMPTOM = 'symptom', 'Symptom'
        TEST_RESULT = 'test_result', 'Test Result'
        DIAGNOSIS = 'diagnosis', 'Diagnosis'
        PRESCRIPTION = 'prescription', 'Prescription'
        NOTE = 'note', 'Clinical Note'

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='medical_records'
    )
    created_by = models.ForeignKey(
        'doctors.Doctor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records'
    )
    record_type = models.CharField(max_length=20, choices=RecordType.choices)
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.record_type} — {self.patient.name}'