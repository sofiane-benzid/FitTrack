from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from home.models import (
    CustomUser, WorkoutTemplate, GymExercise, ExerciseSet, WorkoutSession,
    SessionExercise, SessionSet, Goal, Achievement
)
import math
import json

class ModelTests(TestCase):
    def setUp(self):
        """Set up test data for all model tests."""
        # Create a test user
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass',
            birth_date=date(1995, 5, 15),  # For age calculation
            gender='M',
            weight=75.0,
            height=175.0,
            fitness_level='B',
            xp=1000,
            level=3
        )

        # Create a running workout template
        self.run_template = WorkoutTemplate.objects.create(
            user=self.user,
            name='Morning Run',
            activity_type='R',
            distance=5.0,
            pace='6:00'
        )

        # Create a gym workout template
        self.gym_template = WorkoutTemplate.objects.create(
            user=self.user,
            name='Strength Session',
            activity_type='G'
        )

        # Create a gym exercise
        self.exercise = GymExercise.objects.create(
            template=self.gym_template,
            exercise_name='Bench Press'
        )

        # Create an exercise set
        self.exercise_set = ExerciseSet.objects.create(
            exercise=self.exercise,
            set_number=1,
            reps=10,
            weight=80.0
        )

        # Create a workout session (running)
        self.run_session = WorkoutSession.objects.create(
            user=self.user,
            template=self.run_template,
            activity_type='R',
            distance=5.0,
            duration_seconds=1800,  # 30 minutes
            completed_at=timezone.now()
        )

        # Create a workout session (gym)
        self.gym_session = WorkoutSession.objects.create(
            user=self.user,
            template=self.gym_template,
            activity_type='G',
            duration_seconds=3600,  # 1 hour
            completed_at=timezone.now()
        )

        # Create a session exercise
        self.session_exercise = SessionExercise.objects.create(
            session=self.gym_session,
            exercise_name='Bench Press',
            order=1
        )

        # Create a session set
        self.session_set = SessionSet.objects.create(
            exercise=self.session_exercise,
            set_number=1,
            reps=10,
            weight=80.0,
            completed=True
        )

        # Create a goal
        self.goal = Goal.objects.create(
            user=self.user,
            weekly_workouts=4,
            weekly_distance=20.0
        )

        # Create an achievement
        self.achievement = Achievement.objects.create(
            user=self.user,
            name='First Mile Champion',
            description='Complete your first mile run',
            icon='🏃',
            criteria_type='run_count',
            criteria_value=1,
            xp_reward=50,
            earned_at=timezone.now()
        )

    # CustomUser Tests
    def test_custom_user_str(self):
        """Test the string representation of CustomUser."""
        self.assertEqual(str(self.user), 'testuser')

    def test_custom_user_get_age(self):
        """Test the get_age method of CustomUser."""
        today = date.today()
        expected_age = today.year - 1995 - ((today.month, today.day) < (5, 15))
        self.assertEqual(self.user.get_age(), expected_age)

    def test_custom_user_fields(self):
        """Test that CustomUser fields are set correctly."""
        self.assertEqual(self.user.gender, 'M')
        self.assertEqual(self.user.weight, 75.0)
        self.assertEqual(self.user.height, 175.0)
        self.assertEqual(self.user.fitness_level, 'B')
        self.assertEqual(self.user.xp, 1000)
        self.assertEqual(self.user.level, 3)

    # WorkoutTemplate Tests
    def test_workout_template_str(self):
        """Test the string representation of WorkoutTemplate."""
        self.assertEqual(str(self.run_template), 'Morning Run (Running)')
        self.assertEqual(str(self.gym_template), 'Strength Session (Gym Session)')

    def test_workout_template_get_exercise_count(self):
        """Test the get_exercise_count method of WorkoutTemplate."""
        self.assertEqual(self.gym_template.get_exercise_count(), 1)
        self.assertIsNone(self.run_template.get_exercise_count())

    # GymExercise Tests
    def test_gym_exercise_str(self):
        """Test the string representation of GymExercise."""
        self.assertEqual(str(self.exercise), 'Bench Press (Strength Session)')

    # ExerciseSet Tests
    def test_exercise_set_str(self):
        """Test the string representation of ExerciseSet."""
        self.assertEqual(str(self.exercise_set), 'Set 1 of Bench Press')

    def test_exercise_set_fields(self):
        """Test that ExerciseSet fields are set correctly."""
        self.assertEqual(self.exercise_set.set_number, 1)
        self.assertEqual(self.exercise_set.reps, 10)
        self.assertEqual(self.exercise_set.weight, 80.0)

    # WorkoutSession Tests
    def test_workout_session_str(self):
        """Test the string representation of WorkoutSession."""
        self.assertEqual(
            str(self.run_session),
            f'Morning Run Session ({self.run_session.completed_at})'
        )

    def test_workout_session_get_duration_display(self):
        """Test the get_duration_display method of WorkoutSession."""
        self.assertEqual(self.run_session.get_duration_display(), '30m 0s')
        self.assertEqual(self.gym_session.get_duration_display(), '1h 0m 0s')
        session_no_duration = WorkoutSession.objects.create(
            user=self.user,
            template=self.run_template,
            activity_type='R',
            completed_at=timezone.now()
        )
        self.assertEqual(session_no_duration.get_duration_display(), 'N/A')

    def test_workout_session_get_pace(self):
        """Test the get_pace method of WorkoutSession."""
        # Pace = (1800 s / 60) / 5 km = 6 min/km
        self.assertEqual(self.run_session.get_pace(), '6:00')
        self.assertIsNone(self.gym_session.get_pace())  # Gym session has no pace
        session_no_distance = WorkoutSession.objects.create(
            user=self.user,
            template=self.run_template,
            activity_type='R',
            duration_seconds=1800,
            completed_at=timezone.now()
        )
        self.assertIsNone(session_no_distance.get_pace())

    # SessionExercise Tests
    def test_session_exercise_str(self):
        """Test the string representation of SessionExercise."""
        self.assertEqual(str(self.session_exercise), f'Bench Press (Session {self.gym_session.id})')

    # SessionSet Tests
    def test_session_set_str(self):
        """Test the string representation of SessionSet."""
        self.assertEqual(str(self.session_set), 'Set 1 of Bench Press')

    def test_session_set_fields(self):
        """Test that SessionSet fields are set correctly."""
        self.assertEqual(self.session_set.set_number, 1)
        self.assertEqual(self.session_set.reps, 10)
        self.assertEqual(self.session_set.weight, 80.0)
        self.assertTrue(self.session_set.completed)

    # Goal Tests
    def test_goal_str(self):
        """Test the string representation of Goal."""
        self.assertEqual(str(self.goal), 'Goals for testuser')

    def test_goal_unique_constraint(self):
        """Test that only one Goal can exist per user."""
        with self.assertRaises(Exception):  # IntegrityError
            Goal.objects.create(
                user=self.user,
                weekly_workouts=5,
                weekly_distance=25.0
            )

    def test_goal_fields(self):
        """Test that Goal fields are set correctly."""
        self.assertEqual(self.goal.weekly_workouts, 4)
        self.assertEqual(self.goal.weekly_distance, 20.0)

    # Achievement Tests
    def test_achievement_str(self):
        """Test the string representation of Achievement."""
        self.assertEqual(str(self.achievement), 'First Mile Champion (testuser)')

    def test_achievement_fields(self):
        """Test that Achievement fields are set correctly."""
        self.assertEqual(self.achievement.name, 'First Mile Champion')
        self.assertEqual(self.achievement.description, 'Complete your first mile run')
        self.assertEqual(self.achievement.icon, '🏃')
        self.assertEqual(self.achievement.criteria_type, 'run_count')
        self.assertEqual(self.achievement.criteria_value, 1)
        self.assertEqual(self.achievement.xp_reward, 50)
        self.assertIsNotNone(self.achievement.earned_at)

    def test_achievement_unique_together(self):
        """Test the unique_together constraint for Achievement."""
        with self.assertRaises(Exception):  # IntegrityError
            Achievement.objects.create(
                user=self.user,
                name='First Mile Champion',
                description='Duplicate achievement',
                icon='🏃',
                criteria_type='run_count',
                criteria_value=1,
                xp_reward=50
            )
class ViewTests(TestCase):
    def setUp(self):
        """Set up test data and client for view tests."""
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpass',
            birth_date=date(1995, 5, 15),
            gender='M',
            weight=75.0,
            height=175.0,
            fitness_level='B'
        )
        self.run_template = WorkoutTemplate.objects.create(
            user=self.user,
            name='Morning Run',
            activity_type='R',
            distance=5.0,
            pace='6:00'
        )
        self.gym_template = WorkoutTemplate.objects.create(
            user=self.user,
            name='Strength Session',
            activity_type='G'
        )
        self.run_session = WorkoutSession.objects.create(
            user=self.user,
            template=self.run_template,
            activity_type='R',
            distance=5.0,
            duration_seconds=1800,
            completed_at=timezone.now()
        )
        self.goal = Goal.objects.create(
            user=self.user,
            weekly_workouts=4,
            weekly_distance=20.0
        )
        self.achievement = Achievement.objects.create(
            user=self.user,
            name='First Mile Champion',
            description='Complete your first mile run',
            icon='🏃',
            criteria_type='run_count',
            criteria_value=1,
            xp_reward=50,
            earned_at=timezone.now()
        )

    def test_analytics_view_authenticated(self):
        """Test that analytics view renders with correct context."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('analytics'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home/analytics.html')
        self.assertEqual(response.context['active_page'], 'analytics')
        self.assertIn('sessions', response.context)
        self.assertIn('frequency_data', response.context)
        self.assertIn('distance_data', response.context)
        self.assertIn('pace_data', response.context)
        self.assertIn('strength_data', response.context)
        self.assertIn('volume_data', response.context)
        self.assertIn('goal', response.context)
        self.assertEqual(response.context['sessions'].count(), 1)
        self.assertEqual(response.context['goal'], self.goal)

    def test_achievements_view_authenticated(self):
        """Test that achievements view renders with correct context."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('achievements'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home/achievements.html')
        self.assertEqual(response.context['active_page'], 'achievements')
        self.assertIn('earned_achievements', response.context)
        self.assertIn('in_progress_achievements', response.context)
        self.assertEqual(response.context['earned_achievements'].count(), 1)
        self.assertEqual(response.context['earned_achievements'][0], self.achievement)

    def test_update_goals_view_authenticated(self):
        """Test that update_goals view updates goals and returns JSON."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.post(
            reverse('update_goals'),
            json.dumps({'weeklyWorkouts': 5, 'weeklyDistance': 25.0}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=self.client.cookies.get('csrftoken', '')
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.weekly_workouts, 5)
        self.assertEqual(self.goal.weekly_distance, 25.0)
    def test_ai_coach_view_authenticated(self):
        """Test that aicoach view renders for authenticated users."""
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('aicoach'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home/aicoach.html')
        self.assertEqual(response.context['active_page'], 'aicoach')
