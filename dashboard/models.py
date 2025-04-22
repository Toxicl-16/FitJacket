from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone



class Goal(models.Model):
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateTimeField(null=True, blank=True, default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True, default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    completed = models.BooleanField(default=False)
    abandoned = models.BooleanField(default=False)
    favorite = models.BooleanField(default=False)

    def __str__(self):
        return self.text

    @classmethod
    def expired_goals(cls, user):
        today = timezone.now().date()

        expired = cls.objects.filter(
            user=user,
            completed=False,
            abandoned=False,
            end_date__date__lt=today
        )
        amount_expired = expired.count()
        expired.update(abandoned=True)
        return amount_expired


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    current_streak = models.PositiveIntegerField(default=0)
    max_streak = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username}'s Profile"


class Progress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    goal_name = models.CharField(max_length=100)
    progress_value = models.IntegerField()
    target_value = models.IntegerField()
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.goal_name} ({self.progress_value}/{self.target_value})"

