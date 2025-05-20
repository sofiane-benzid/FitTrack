from datetime import date

from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


# Create your models here.
class CustomUser(AbstractUser):
    birth_date = models.DateField(null=True, blank=True)

    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)

    weight = models.FloatField(null=True, blank=True, help_text="Weight in kilograms")
    height = models.FloatField(null=True, blank=True, help_text="Height in centimeters")
    xp = models.IntegerField(default=0)  # Total XP earned
    level = models.IntegerField(default=1)  # Current level

    FITNESS_LEVEL_CHOICES = (
        ('B', 'Beginner'),
        ('I', 'Intermediate'),
        ('A', 'Advanced'),
    )
    fitness_level = models.CharField(
        max_length=1,
        choices=FITNESS_LEVEL_CHOICES,
        default='B',
        blank=True,
    )

    def get_age(self):
        if self.birth_date:
            today = date.today()
            return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        return None

    def __str__(self):
        return self.username

class WorkoutTemplate(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='templates')
    name = models.CharField(max_length=100)  # e.g., "Morning run"
    ACTIVITY_TYPES = (
        ('R', 'Running'),
        ('G', 'Gym Session'),
    )
    activity_type = models.CharField(max_length=1, choices=ACTIVITY_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    # Running-specific fields
    distance = models.FloatField(null=True, blank=True, help_text="Distance in kilometers")
    pace = models.CharField(max_length=5, null=True, blank=True, help_text="Pace in min/km, e.g., 5:30")

    def __str__(self):
        return f"{self.name} ({self.get_activity_type_display()})"
    def pace_to_minutes(self):
        """Convert pace (e.g., '5' or '5:30') to total minutes per km as a float."""
        if not self.pace:
            return None
        try:
            return float(self.pace)  # Treat as minutes only, e.g., "5" -> 5.0
        except (ValueError, AttributeError):
            return None
    def get_speed(self):
        """Calculate speed in km/h from distance and pace."""
        if self.activity_type != 'R' or not self.distance or not self.pace:
            return None
        pace_minutes = self.pace_to_minutes()
        if pace_minutes is None or pace_minutes == 0:
            return None
        # Speed (km/h) = Distance (km) / Time (h) = Distance / (Pace in min/km * Distance / 60)
        # Simplified: Speed = 60 / Pace (min/km)
        return round(60 / pace_minutes, 2)

    def get_duration(self):
        """Calculate total duration in minutes from distance and pace."""
        if self.activity_type != 'R' or not self.distance or not self.pace:
            return None
        pace_minutes = self.pace_to_minutes()
        if pace_minutes is None:
            return None
        # Duration (min) = Distance (km) * Pace (min/km)
        total_minutes = self.distance * pace_minutes
        return round(total_minutes, 1)

    def get_duration_display(self):
        """Format duration as 'Xh Ym' or 'Ym'."""
        minutes = self.get_duration()
        if minutes is None:
            return "N/A"
        hours = int(minutes // 60)
        remaining_minutes = int(minutes % 60)
        if hours > 0:
            return f"{hours}h {remaining_minutes}m"
        return f"{remaining_minutes}m"

    def get_exercise_count(self):
        """Return the number of exercises for a gym session."""
        if self.activity_type != 'G':
            return None
        return self.exercises.count()

class GymExercise(models.Model):
    template = models.ForeignKey(WorkoutTemplate, on_delete=models.CASCADE, related_name='exercises')
    exercise_name = models.CharField(max_length=100)  # e.g., "Bench Press"

    def __str__(self):
        return f"{self.exercise_name} ({self.template.name})"

class ExerciseSet(models.Model):
    exercise = models.ForeignKey(GymExercise, on_delete=models.CASCADE, related_name='sets')
    set_number = models.PositiveIntegerField()  # e.g., 1, 2, 3
    reps = models.PositiveIntegerField()
    weight = models.FloatField(null=True, blank=True, help_text="Weight in kilograms")

    def __str__(self):
        return f"Set {self.set_number} of {self.exercise.exercise_name}"

class WorkoutSession(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sessions')
    template = models.ForeignKey(WorkoutTemplate, on_delete=models.CASCADE, related_name='sessions')
    activity_type = models.CharField(max_length=1, choices=WorkoutTemplate.ACTIVITY_TYPES)
    distance = models.FloatField(null=True, blank=True, help_text="Distance in kilometers")  # For running
    duration_seconds = models.IntegerField(null=True, blank=True, help_text="Duration in seconds")  # For both running and gym
    completed_at = models.DateTimeField(default=timezone.now)

    def get_duration_display(self):
        """Format duration as 'Xh Ym' or 'Ym'."""
        if self.duration_seconds is None:
            return "N/A"
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        hours = int(minutes // 60)
        remaining_minutes = int(minutes % 60)
        if hours > 0:
            return f"{hours}h {remaining_minutes}m {seconds}s"
        return f"{remaining_minutes}m {seconds}s"

    def get_pace(self):
        """Calculate pace in min/km for running sessions."""
        if self.activity_type != 'R' or not self.distance or not self.duration_seconds or self.distance == 0:
            return None
        pace_minutes = (self.duration_seconds / 60) / self.distance  # min/km
        minutes = int(pace_minutes)
        seconds = int((pace_minutes - minutes) * 60)
        return f"{minutes}:{seconds:02d}"

    def __str__(self):
        return f"{self.template.name} Session ({self.completed_at})"

class SessionExercise(models.Model):
    session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name='exercises')
    exercise_name = models.CharField(max_length=100)
    order = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.exercise_name} (Session {self.session.id})"

class SessionSet(models.Model):
    exercise = models.ForeignKey(SessionExercise, on_delete=models.CASCADE, related_name='sets')
    set_number = models.PositiveIntegerField()
    reps = models.PositiveIntegerField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True, help_text="Weight in kilograms")
    completed = models.BooleanField(default=False)  # New field

    def __str__(self):
        return f"Set {self.set_number} of {self.exercise.exercise_name}"

class Goal(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='goals')
    weekly_workouts = models.PositiveIntegerField(default=4, help_text="Target number of workouts per week")
    weekly_distance = models.FloatField(default=20, help_text="Target running distance in kilometers per week")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Goals for {self.user.username}"

    class Meta:
        # Ensure one goal set per user
        constraints = [
            models.UniqueConstraint(fields=['user'], name='unique_user_goal')
        ]

class Achievement(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='achievements')
    name = models.CharField(max_length=100)  # e.g., "First Mile Champion"
    description = models.CharField(max_length=200)  # e.g., "Complete your first mile run"
    icon = models.CharField(max_length=10)
    criteria_type = models.CharField(max_length=50)  # e.g., "run_count", "gym_count"
    criteria_value = models.IntegerField()  # e.g., 1 (first run), 10 (10 gym sessions)
    xp_reward = models.IntegerField(default=100)  # XP for earning the achievement
    earned_at = models.DateTimeField(null=True, blank=True)  # Null if not earned
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')  # One achievement per user per type

    def __str__(self):
        return f"{self.name} ({self.user.username})"