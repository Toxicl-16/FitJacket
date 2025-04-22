from django.contrib.auth.models import User
from django.db import models

# Create your models here.

class Event(models.Model):
    name = models.CharField(max_length=255)
    workout_type = models.CharField(
        max_length=20,
        choices=[
            ('strength', 'Strength'),
            ('cardio', 'Cardio'),
            ('yoga', 'Yoga'),
        ]
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_event')
    created_at = models.DateTimeField(auto_now_add=True)