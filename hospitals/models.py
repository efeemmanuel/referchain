from django.db import models

# Create your models here.

from django.db import models
from django.conf import settings


class Hospital(models.Model):
    class Tier(models.TextChoices):
        PRIMARY = 'primary', 'Primary'
        SECONDARY = 'secondary', 'Secondary'
        TERTIARY = 'tertiary', 'Tertiary'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hospital'
    )
    name = models.CharField(max_length=255)
    address = models.TextField()
    tier = models.CharField(max_length=20, choices=Tier.choices)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
