import openai
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from django.db.models import Sum, Count, Max, F
from django.db.models.functions import TruncDate, TruncMonth
from datetime import datetime, timedelta
import json
import math
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from home.models import CustomUser, WorkoutTemplate, GymExercise, ExerciseSet, WorkoutSession, SessionExercise, \
    SessionSet, Goal, Achievement
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

def track(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))
    templates = WorkoutTemplate.objects.filter(user=request.user).order_by('-created_at')
    templates_with_session_data = []
    for template in templates:
        recent_session = WorkoutSession.objects.filter(
            user=request.user,
            template=template,
        ).order_by('-completed_at').first()
        templates_with_session_data.append({
            'template': template,
            'latest_duration': recent_session.get_duration_display() if recent_session else None,
            'latest_distance': recent_session.distance if recent_session else None,
        })
    return render(request, 'home/track.html', {
        'active_page': 'track',
        'templates_with_session_data': templates_with_session_data,
    })

@login_required
def analytics(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))

    # Get filter parameters
    activity_filter = request.GET.get('activity', 'all')
    date_filter = request.GET.get('date', 'all')
    freq_period = request.GET.get('freq_period', 'weekly')
    dist_period = request.GET.get('dist_period', 'weekly')
    pace_period = request.GET.get('pace_period', 'weekly')
    strength_period = request.GET.get('strength_period', 'weekly')
    volume_period = request.GET.get('volume_period', 'weekly')
    freq_activity_type = request.GET.get('freq_activity_type', 'all')
    strength_exercise = request.GET.get('strength_exercise', 'all')
    volume_exercise = request.GET.get('volume_exercise', 'all')
    # Time range parameters for each chart
    freq_time_range = request.GET.get('freq_time_range', 'recent')
    dist_time_range = request.GET.get('dist_time_range', 'recent')
    pace_time_range = request.GET.get('pace_time_range', 'recent')
    strength_time_range = request.GET.get('strength_time_range', 'recent')
    volume_time_range = request.GET.get('volume_time_range', 'recent')

    # Base queryset for sessions (history table)
    sessions = WorkoutSession.objects.filter(user=request.user).order_by('-completed_at')
    if activity_filter == 'R':
        sessions = sessions.filter(activity_type='R')
    elif activity_filter == 'G':
        sessions = sessions.filter(activity_type='G')
    today = datetime.now()
    if date_filter == '7':
        sessions = sessions.filter(completed_at__gte=today - timedelta(days=7))
    elif date_filter == '30':
        sessions = sessions.filter(completed_at__gte=today - timedelta(days=30))

    # Base querysets
    freq_sessions = WorkoutSession.objects.filter(user=request.user)
    run_sessions = WorkoutSession.objects.filter(user=request.user, activity_type='R')
    gym_sessions = WorkoutSession.objects.filter(user=request.user, activity_type='G')
    if freq_activity_type == 'R':
        freq_sessions = freq_sessions.filter(activity_type='R')
    elif freq_activity_type == 'G':
        freq_sessions = freq_sessions.filter(activity_type='G')
    if activity_filter == 'R':
        run_sessions = run_sessions.filter(activity_type='R')
    elif activity_filter == 'G':
        run_sessions = run_sessions.filter(activity_type='G')

    # Data calculation
    today_date = today.date()
    six_weeks_ago = today_date - timedelta(weeks=6)
    frequency_data = {'daily': {}, 'weekly': {}, 'monthly': {}}
    distance_data = {}
    pace_data = {}
    strength_data = {'daily': {}, 'weekly': {}, 'monthly': {}}
    volume_data = {'daily': {}, 'weekly': {}, 'monthly': {}}

    # Determine time range for each chart
    earliest_session = freq_sessions.order_by('completed_at').first()
    earliest_date = earliest_session.completed_at.date() if earliest_session else today_date
    weeks_diff = (today_date - earliest_date).days // 7 + 1  # Total weeks, including partial
    six_months_ago = today_date - timedelta(days=180)

    # Frequency Chart Time Range
    freq_daily_weekly_filter = {} if freq_time_range == 'all' else {'completed_at__date__gte': six_weeks_ago}
    freq_monthly_filter = {} if freq_time_range == 'all' else {'completed_at__date__gte': six_months_ago}

    # Distance Chart Time Range
    dist_daily_weekly_filter = {} if dist_time_range == 'all' else {'completed_at__date__gte': six_weeks_ago}
    dist_monthly_filter = {} if dist_time_range == 'all' else {'completed_at__date__gte': six_months_ago}

    # Pace Chart Time Range
    pace_daily_weekly_filter = {} if pace_time_range == 'all' else {'completed_at__date__gte': six_weeks_ago}
    pace_monthly_filter = {} if pace_time_range == 'all' else {'completed_at__date__gte': six_months_ago}

    # Strength Chart Time Range
    strength_daily_weekly_filter = {} if strength_time_range == 'all' else {'exercise__session__completed_at__date__gte': six_weeks_ago}
    strength_monthly_filter = {} if strength_time_range == 'all' else {'exercise__session__completed_at__date__gte': six_months_ago}

    # Volume Chart Time Range
    volume_daily_weekly_filter = {} if volume_time_range == 'all' else {'exercise__session__completed_at__date__gte': six_weeks_ago}
    volume_monthly_filter = {} if volume_time_range == 'all' else {'exercise__session__completed_at__date__gte': six_months_ago}

    # Daily - Frequency
    for activity in ['all', 'R', 'G']:
        freq_qs = freq_sessions
        if activity != 'all':
            freq_qs = freq_qs.filter(activity_type=activity)
        freq_data = freq_qs.filter(**freq_daily_weekly_filter).annotate(
            day=TruncDate('completed_at')
        ).values('day').annotate(count=Count('id')).order_by('day')
        frequency_data['daily'][activity] = [
            {'label': entry['day'].strftime('%b %d'), 'count': entry['count']}
            for entry in freq_data
        ]

    # Daily - Distance
    dist_data = run_sessions.filter(**dist_daily_weekly_filter).annotate(
        day=TruncDate('completed_at')
    ).values('day').annotate(total_distance=Sum('distance')).order_by('day')
    distance_data['daily'] = [
        {'label': entry['day'].strftime('%b %d'), 'distance': float(entry['total_distance']) if entry['total_distance'] else 0}
        for entry in dist_data
    ]

    # Daily - Pace
    pace_data_daily = run_sessions.filter(
        **pace_daily_weekly_filter,
        distance__gt=0,
        duration_seconds__gt=0
    ).annotate(
        day=TruncDate('completed_at')
    ).values('day').annotate(
        total_distance=Sum('distance'),
        total_duration=Sum('duration_seconds')
    ).order_by('day')
    pace_data['daily'] = [
        {
            'label': entry['day'].strftime('%b %d'),
            'pace': (entry['total_duration'] / 60.0) / entry['total_distance'] if entry['total_distance'] else 0
        }
        for entry in pace_data_daily
    ]

    # Strength - Daily
    exercises = sorted(gym_sessions.values_list('exercises__exercise_name', flat=True).distinct().exclude(exercises__exercise_name__isnull=True))
    all_days = sorted(set(gym_sessions.filter(
        **freq_daily_weekly_filter
    ).annotate(
        day=TruncDate('completed_at')
    ).values_list('day', flat=True)))

    # Precompute max weight and reps per day and exercise, prioritizing higher reps when weights are equal
    strength_daily = SessionSet.objects.filter(
        exercise__session__user=request.user,
        exercise__session__activity_type='G',
        weight__isnull=False
    ).filter(**strength_daily_weekly_filter).annotate(
        day=TruncDate('exercise__session__completed_at')
    ).values('day', 'exercise__exercise_name').annotate(
        max_weight=Max('weight')
    ).order_by('day')

    strength_daily_dict = {}
    for entry in strength_daily:
        day = entry['day']
        exercise = entry['exercise__exercise_name']
        max_weight = entry['max_weight']
        if day not in strength_daily_dict:
            strength_daily_dict[day] = {}
        # Find the set with the max weight and highest reps
        max_set = SessionSet.objects.filter(
            exercise__session__user=request.user,
            exercise__session__activity_type='G',
            exercise__session__completed_at__date=day,
            exercise__exercise_name=exercise,
            weight=max_weight
        ).order_by('-reps', '-id').first()  # Order by reps descending, then id to break ties
        reps = max_set.reps if max_set else 0
        strength_daily_dict[day][exercise] = {'weight': float(max_weight), 'reps': reps}

    for exercise in exercises:
        if exercise:
            daily_data = [
                {
                    'label': day.strftime('%b %d'),
                    'weight': strength_daily_dict.get(day, {}).get(exercise, {'weight': 0, 'reps': 0})['weight'],
                    'reps': strength_daily_dict.get(day, {}).get(exercise, {'weight': 0, 'reps': 0})['reps']
                }
                for day in all_days
            ]
            strength_data['daily'][exercise] = daily_data

    # Compute max weight across all exercises per day
    strength_daily_all = SessionSet.objects.filter(
        exercise__session__user=request.user,
        exercise__session__activity_type='G',
        weight__isnull=False
    ).filter(**strength_daily_weekly_filter).annotate(
        day=TruncDate('exercise__session__completed_at')
    ).values('day').annotate(
        max_weight=Max('weight')
    ).order_by('day')

    strength_daily_all_dict = {}
    for entry in strength_daily_all:
        day = entry['day']
        max_weight = entry['max_weight']
        max_set = SessionSet.objects.filter(
            exercise__session__user=request.user,
            exercise__session__activity_type='G',
            exercise__session__completed_at__date=day,
            weight=max_weight
        ).order_by('-reps', '-id').first()
        reps = max_set.reps if max_set else 0
        strength_daily_all_dict[day] = {'weight': float(max_weight), 'reps': reps}

    strength_data['daily']['all'] = [
        {
            'label': day.strftime('%b %d'),
            'weight': strength_daily_all_dict.get(day, {'weight': 0, 'reps': 0})['weight'],
            'reps': strength_daily_all_dict.get(day, {'weight': 0, 'reps': 0})['reps']
        }
        for day in all_days
    ]

    # Volume - Daily
    volume_daily = SessionSet.objects.filter(
        exercise__session__user=request.user,
        exercise__session__activity_type='G'
    ).filter(**volume_daily_weekly_filter).annotate(
        day=TruncDate('exercise__session__completed_at')
    ).values('day', 'exercise__exercise_name').annotate(
        volume=Sum(F('weight') * F('reps'))
    ).order_by('day')

    volume_daily_dict = {}
    for entry in volume_daily:
        day = entry['day']
        exercise = entry['exercise__exercise_name']
        if day not in volume_daily_dict:
            volume_daily_dict[day] = {}
        volume_daily_dict[day][exercise] = float(entry['volume'] or 0)

    # Compute total volume across all exercises per day
    volume_daily_all = SessionSet.objects.filter(
        exercise__session__user=request.user,
        exercise__session__activity_type='G'
    ).filter(**volume_daily_weekly_filter).annotate(
        day=TruncDate('exercise__session__completed_at')
    ).values('day').annotate(
        total_volume=Sum(F('weight') * F('reps'))
    ).order_by('day')

    volume_daily_all_dict = {entry['day']: float(entry['total_volume'] or 0) for entry in volume_daily_all}

    for exercise in exercises:
        if exercise:
            daily_data = [
                {
                    'label': day.strftime('%b %d'),
                    'volume': volume_daily_dict.get(day, {}).get(exercise, 0)
                }
                for day in all_days
            ]
            volume_data['daily'][exercise] = daily_data

    volume_data['daily']['all'] = [
        {
            'label': day.strftime('%b %d'),
            'volume': volume_daily_all_dict.get(day, 0),
            'by_exercise': volume_daily_dict.get(day, {})
        }
        for day in all_days
    ]

    # Weekly - Frequency
    for activity in ['all', 'R', 'G']:
        freq_qs = freq_sessions
        if activity != 'all':
            freq_qs = freq_qs.filter(activity_type='activity')
        weekly_freq_data = []
        weeks_to_show = weeks_diff if freq_time_range == 'all' else 6
        week_start_base = earliest_date if freq_time_range == 'all' else six_weeks_ago
        for i in range(weeks_to_show):
            week_start = week_start_base + timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            if i == weeks_to_show - 1 and week_end < today_date:
                week_end = today_date
            freq_count = freq_qs.filter(
                completed_at__date__gte=week_start,
                completed_at__date__lte=week_end
            ).count()
            week_label = f"Week {i + 1}"
            date_range = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"
            weekly_freq_data.append({
                'label': week_label,
                'date_range': date_range,
                'count': freq_count
            })
        frequency_data['weekly'][activity] = weekly_freq_data

    # Weekly - Distance
    weekly_dist_data = []
    weeks_to_show = weeks_diff if dist_time_range == 'all' else 6
    week_start_base = earliest_date if dist_time_range == 'all' else six_weeks_ago
    for i in range(weeks_to_show):
        week_start = week_start_base + timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)
        if i == weeks_to_show - 1 and week_end < today_date:
            week_end = today_date
        dist_sum = run_sessions.filter(
            completed_at__date__gte=week_start,
            completed_at__date__lte=week_end
        ).aggregate(total=Sum('distance'))['total'] or 0
        week_label = f"Week {i + 1}"
        date_range = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"
        weekly_dist_data.append({
            'label': week_label,
            'date_range': date_range,
            'distance': float(dist_sum)
        })
    distance_data['weekly'] = weekly_dist_data

    # Weekly - Pace
    weekly_pace_data = []
    weeks_to_show = weeks_diff if pace_time_range == 'all' else 6
    week_start_base = earliest_date if pace_time_range == 'all' else six_weeks_ago
    for i in range(weeks_to_show):
        week_start = week_start_base + timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)
        if i == weeks_to_show - 1 and week_end < today_date:
            week_end = today_date
        pace_agg = run_sessions.filter(
            completed_at__date__gte=week_start,
            completed_at__date__lte=week_end,
            distance__gt=0,
            duration_seconds__gt=0
        ).aggregate(
            total_distance=Sum('distance'),
            total_duration=Sum('duration_seconds')
        )
        week_label = f"Week {i + 1}"
        date_range = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"
        pace = (pace_agg['total_duration'] / 60.0) / pace_agg['total_distance'] if pace_agg['total_duration'] and pace_agg['total_distance'] else 0
        weekly_pace_data.append({
            'label': week_label,
            'date_range': date_range,
            'pace': pace
        })
    pace_data['weekly'] = weekly_pace_data

    # Strength - Weekly
    weeks_to_show = weeks_diff if strength_time_range == 'all' else 6
    week_start_base = earliest_date if strength_time_range == 'all' else six_weeks_ago
    for i in range(weeks_to_show):
        week_start = week_start_base + timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)
        if i == weeks_to_show - 1 and week_end < today_date:
            week_end = today_date
        week_label = f"Week {i + 1}"
        date_range = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"

        # Precompute max weight and reps per week and exercise, prioritizing higher reps
        strength_weekly = SessionSet.objects.filter(
            exercise__session__user=request.user,
            exercise__session__activity_type='G',
            exercise__session__completed_at__date__gte=week_start,
            exercise__session__completed_at__date__lte=week_end,
            weight__isnull=False
        ).values('exercise__exercise_name').annotate(
            max_weight=Max('weight')
        )

        strength_weekly_dict = {}
        for entry in strength_weekly:
            exercise = entry['exercise__exercise_name']
            max_weight = entry['max_weight']
            max_set = SessionSet.objects.filter(
                exercise__session__user=request.user,
                exercise__session__activity_type='G',
                exercise__session__completed_at__date__gte=week_start,
                exercise__session__completed_at__date__lte=week_end,
                exercise__exercise_name=exercise,
                weight=max_weight
            ).order_by('-reps', '-id').first()  # Order by reps descending
            reps = max_set.reps if max_set else 0
            strength_weekly_dict[exercise] = {'weight': float(max_weight), 'reps': reps}


        for exercise in exercises:
            if exercise:
                weekly_data = [{
                    'label': week_label,
                    'date_range': date_range,
                    'weight': strength_weekly_dict.get(exercise, {'weight': 0, 'reps': 0})['weight'],
                    'reps': strength_weekly_dict.get(exercise, {'weight': 0, 'reps': 0})['reps']
                }]
                strength_data['weekly'][exercise] = strength_data['weekly'].get(exercise, []) + (weekly_data or [{'label': week_label, 'date_range': date_range, 'weight': 0, 'reps': 0}])

        # Max weight across all exercises for the week
        max_set_all = SessionSet.objects.filter(
            exercise__session__user=request.user,
            exercise__session__activity_type='G',
            exercise__session__completed_at__date__gte=week_start,
            exercise__session__completed_at__date__lte=week_end,
            weight__isnull=False
        ).order_by('-weight', '-reps', '-id').first()
        all_max = max_set_all.weight if max_set_all else 0
        all_reps = max_set_all.reps if max_set_all else 0
        strength_data['weekly']['all'] = strength_data['weekly'].get('all', []) + [
            {
                'label': week_label,
                'date_range': date_range,
                'weight': float(all_max),
                'reps': all_reps
            }
        ]

    # Volume - Weekly
    weeks_to_show = weeks_diff if volume_time_range == 'all' else 6
    week_start_base = earliest_date if volume_time_range == 'all' else six_weeks_ago
    volume_weekly_dict = {}
    volume_weekly_all_dict = {}
    for i in range(weeks_to_show):
        week_start = week_start_base + timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)
        if i == weeks_to_show - 1 and week_end < today_date:
            week_end = today_date
        week_label = f"Week {i + 1}"
        date_range = f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d')}"
        volume_by_exercise = SessionSet.objects.filter(
            exercise__session__user=request.user,
            exercise__session__activity_type='G',
            exercise__session__completed_at__date__gte=week_start,
            exercise__session__completed_at__date__lte=week_end
        ).values('exercise__exercise_name').annotate(
            volume=Sum(F('weight') * F('reps'))
        )
        volume_total = SessionSet.objects.filter(
            exercise__session__user=request.user,
            exercise__session__activity_type='G',
            exercise__session__completed_at__date__gte=week_start,
            exercise__session__completed_at__date__lte=week_end
        ).aggregate(total_volume=Sum(F('weight') * F('reps')))['total_volume'] or 0

        by_exercise = {ex['exercise__exercise_name']: float(ex['volume'] or 0) for ex in volume_by_exercise}
        volume_weekly_dict[week_label] = by_exercise
        volume_weekly_all_dict[week_label] = {
            'label': week_label,
            'date_range': date_range,
            'volume': float(volume_total),
            'by_exercise': by_exercise
        }

    for exercise in exercises:
        if exercise:
            weekly_data = [
                {
                    'label': week_label,
                    'date_range': date_range,
                    'volume': volume_weekly_dict.get(week_label, {}).get(exercise, 0)
                }
                for week_label, date_range in [(entry['label'], entry['date_range']) for entry in volume_weekly_all_dict.values()]
            ]
            volume_data['weekly'][exercise] = weekly_data

    volume_data['weekly']['all'] = list(volume_weekly_all_dict.values())

    # Monthly - Frequency
    for activity in ['all', 'R', 'G']:
        freq_qs = freq_sessions
        if activity != 'all':
            freq_qs = freq_qs.filter(activity_type=activity)
        freq_data = freq_qs.filter(**freq_monthly_filter).annotate(
            month=TruncMonth('completed_at')
        ).values('month').annotate(count=Count('id')).order_by('month')
        frequency_data['monthly'][activity] = [
            {'label': entry['month'].strftime('%b %Y'), 'count': entry['count']}
            for entry in freq_data
        ]

    # Monthly - Distance
    dist_data = run_sessions.filter(**dist_monthly_filter).annotate(
        month=TruncMonth('completed_at')
    ).values('month').annotate(total_distance=Sum('distance')).order_by('month')
    distance_data['monthly'] = [
        {'label': entry['month'].strftime('%b %Y'), 'distance': float(entry['total_distance']) if entry['total_distance'] else 0}
        for entry in dist_data
    ]

    # Monthly - Pace
    pace_data_monthly = run_sessions.filter(
        **pace_monthly_filter,
        distance__gt=0,
        duration_seconds__gt=0
    ).annotate(
        month=TruncMonth('completed_at')
    ).values('month').annotate(
        total_distance=Sum('distance'),
        total_duration=Sum('duration_seconds')
    ).order_by('month')
    pace_data['monthly'] = [
        {
            'label': entry['month'].strftime('%b %Y'),
            'pace': (entry['total_duration'] / 60.0) / entry['total_distance'] if entry['total_distance'] else 0
        }
        for entry in pace_data_monthly
    ]

    # Strength - Monthly
    strength_monthly = SessionSet.objects.filter(
        exercise__session__user=request.user,
        exercise__session__activity_type='G',
        weight__isnull=False
    ).filter(**strength_monthly_filter).annotate(
        month=TruncMonth('exercise__session__completed_at')
    ).values('month', 'exercise__exercise_name').annotate(
        max_weight=Max('weight')
    ).order_by('month')

    all_months = sorted(set(strength_monthly.values_list('month', flat=True)))
    strength_monthly_dict = {}
    for entry in strength_monthly:
        month = entry['month']
        exercise = entry['exercise__exercise_name']
        max_weight = entry['max_weight']
        if month not in strength_monthly_dict:
            strength_monthly_dict[month] = {}
        max_set = SessionSet.objects.filter(
            exercise__session__user=request.user,
            exercise__session__activity_type='G',
            exercise__session__completed_at__year=month.year,
            exercise__session__completed_at__month=month.month,
            exercise__exercise_name=exercise,
            weight=max_weight
        ).order_by('-reps', '-id').first()  # Order by reps descending
        reps = max_set.reps if max_set else 0
        strength_monthly_dict[month][exercise] = {'weight': float(max_weight), 'reps': reps}

    for exercise in exercises:
        if exercise:
            monthly_data = [
                {
                    'label': month.strftime('%b %Y'),
                    'weight': strength_monthly_dict.get(month, {}).get(exercise, {'weight': 0, 'reps': 0})['weight'],
                    'reps': strength_monthly_dict.get(month, {}).get(exercise, {'weight': 0, 'reps': 0})['reps']
                }
                for month in all_months
            ]
            strength_data['monthly'][exercise] = monthly_data

    # Max weight across all exercises for the month
    strength_monthly_all = SessionSet.objects.filter(
        exercise__session__user=request.user,
        exercise__session__activity_type='G',
        weight__isnull=False
    ).filter(**strength_monthly_filter).annotate(
        month=TruncMonth('exercise__session__completed_at')
    ).values('month').annotate(
        max_weight=Max('weight')
    ).order_by('month')

    strength_monthly_all_dict = {}
    for entry in strength_monthly_all:
        month = entry['month']
        max_weight = entry['max_weight']
        max_set = SessionSet.objects.filter(
            exercise__session__user=request.user,
            exercise__session__activity_type='G',
            exercise__session__completed_at__year=month.year,
            exercise__session__completed_at__month=month.month,
            weight=max_weight
        ).order_by('-reps', '-id').first()
        reps = max_set.reps if max_set else 0
        strength_monthly_all_dict[month] = {'weight': float(max_weight), 'reps': reps}


    strength_data['monthly']['all'] = [
        {
            'label': month.strftime('%b %Y'),
            'weight': strength_monthly_all_dict.get(month, {'weight': 0, 'reps': 0})['weight'],
            'reps': strength_monthly_all_dict.get(month, {'weight': 0, 'reps': 0})['reps']
        }
        for month in all_months
    ]

    # Volume - Monthly
    volume_monthly = SessionSet.objects.filter(
        exercise__session__user=request.user,
        exercise__session__activity_type='G'
    ).filter(**volume_monthly_filter).annotate(
        month=TruncMonth('exercise__session__completed_at')
    ).values('month', 'exercise__exercise_name').annotate(
        volume=Sum(F('weight') * F('reps'))
    ).order_by('month')

    volume_monthly_dict = {}
    for entry in volume_monthly:
        month = entry['month'].strftime('%b %Y')
        exercise = entry['exercise__exercise_name']
        if month not in volume_monthly_dict:
            volume_monthly_dict[month] = {}
        volume_monthly_dict[month][exercise] = float(entry['volume'] or 0)

    # Compute total volume across all exercises per month
    volume_monthly_all = SessionSet.objects.filter(
        exercise__session__user=request.user,
        exercise__session__activity_type='G'
    ).filter(**volume_monthly_filter).annotate(
        month=TruncMonth('exercise__session__completed_at')
    ).values('month').annotate(
        total_volume=Sum(F('weight') * F('reps'))
    ).order_by('month')

    volume_monthly_all_dict = {}
    for entry in volume_monthly_all:
        month_label = entry['month'].strftime('%b %Y')
        volume_monthly_all_dict[month_label] = {
            'label': month_label,
            'date_range': month_label,
            'volume': float(entry['total_volume'] or 0),
            'by_exercise': volume_monthly_dict.get(month_label, {})
        }

    for exercise in exercises:
        if exercise:
            monthly_data = [
                {
                    'label': month_label,
                    'date_range': month_label,
                    'volume': volume_monthly_dict.get(month_label, {}).get(exercise, 0)
                }
                for month_label in volume_monthly_all_dict.keys()
            ]
            volume_data['monthly'][exercise] = monthly_data

    volume_data['monthly']['all'] = list(volume_monthly_all_dict.values())

    # Get or create user's goals
    try:
        goal, created = Goal.objects.get_or_create(user=request.user)

    except Exception as e:

        goal = None
        created = False

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    completed_workouts = WorkoutSession.objects.filter(
        user=request.user,
        completed_at__range=[week_start, week_end]
    ).count()
    completed_distance = WorkoutSession.objects.filter(
        user=request.user,
        activity_type='R',
        completed_at__range=[week_start, week_end]
    ).aggregate(total=Sum('distance'))['total'] or 0

    # Calculate progress percentages
    workout_progress_percent = int((completed_workouts / goal.weekly_workouts * 100) if goal and goal.weekly_workouts > 0 else 0)
    distance_progress_percent = int((completed_distance / goal.weekly_distance * 100) if goal and goal.weekly_distance > 0 else 0)

    return render(request, 'home/analytics.html', {
        'active_page': 'analytics',
        'sessions': sessions,
        'activity_filter': activity_filter,
        'date_filter': date_filter,
        'freq_period': freq_period,
        'dist_period': dist_period,
        'pace_period': pace_period,
        'strength_period': strength_period,
        'volume_period': volume_period,
        'freq_activity_type': freq_activity_type,
        'strength_exercise': strength_exercise,
        'volume_exercise': volume_exercise,
        'freq_time_range': freq_time_range,
        'dist_time_range': dist_time_range,
        'pace_time_range': pace_time_range,
        'strength_time_range': strength_time_range,
        'volume_time_range': volume_time_range,
        'frequency_data': json.dumps(frequency_data),
        'distance_data': json.dumps(distance_data),
        'pace_data': json.dumps(pace_data),
        'strength_data': json.dumps(strength_data),
        'volume_data': json.dumps(volume_data),
        'exercises': exercises,
        'goal': goal,
        'completed_workouts': completed_workouts,
        'completed_distance': completed_distance,
        'workout_progress_percent': workout_progress_percent,
        'distance_progress_percent': distance_progress_percent,
        'goal_workouts': goal.weekly_workouts if goal else 4,
        'goal_distance': goal.weekly_distance if goal else 20,
    })

@login_required
def update_goals(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            weekly_workouts = data.get('weeklyWorkouts')
            weekly_distance = data.get('weeklyDistance')

            # Validate inputs
            weekly_workouts = int(weekly_workouts) if weekly_workouts is not None else None
            weekly_distance = float(weekly_distance) if weekly_distance is not None else None

            if not (1 <= weekly_workouts <= 14):

                return JsonResponse({'status': 'error', 'message': 'Workouts must be between 1 and 14'}, status=400)
            if not (1 <= weekly_distance <= 100):

                return JsonResponse({'status': 'error', 'message': 'Distance must be between 1 and 100 km'}, status=400)

            goal, created = Goal.objects.get_or_create(user=request.user)
            goal.weekly_workouts = weekly_workouts
            goal.weekly_distance = weekly_distance
            goal.save()


            return JsonResponse({
                'status': 'success',
                'weekly_workouts': goal.weekly_workouts,
                'weekly_distance': goal.weekly_distance
            })
        except (ValueError, TypeError, KeyError) as e:

            return JsonResponse({'status': 'error', 'message': f'Invalid data: {str(e)}'}, status=400)
        except Exception as e:

            return JsonResponse({'status': 'error', 'message': 'Server error'}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

@login_required
def session_detail(request, session_id):
    session = get_object_or_404(WorkoutSession, id=session_id, user=request.user)
    context = {
        'session': session,
        'active_page': 'analytics',  # sidebar highlighting
    }
    return render(request, 'home/session_detail.html', context)

@login_required
def achievements(request):
    user = request.user
    achievements = Achievement.objects.filter(user=user)
    earned_achievements = achievements.exclude(earned_at__isnull=True)
    in_progress_achievements = achievements.filter(earned_at__isnull=True)

    # Calculate stats
    earned_achievements_count = earned_achievements.count()
    total_achievements = achievements.count()
    completion_percent = int((earned_achievements_count / total_achievements * 100) if total_achievements > 0 else 0)
    next_level_xp = user.level * 500
    xp_progress_percent = int((user.xp / next_level_xp) * 100) if next_level_xp > 0 else 0

    # Session counts for progress
    user_run_count = WorkoutSession.objects.filter(user=user, activity_type='R').count()
    user_gym_count = WorkoutSession.objects.filter(user=user, activity_type='G').count()
    total_distance = WorkoutSession.objects.filter(user=user, activity_type='R').aggregate(total=Sum('distance'))['total'] or 0
    total_volume = SessionSet.objects.filter(
        exercise__session__user=user,
        exercise__session__activity_type='G',
        completed=True,
        weight__gt=0,
        reps__gt=0
    ).aggregate(total=Sum(F('weight') * F('reps')))['total'] or 0
    total_workouts = WorkoutSession.objects.filter(user=user).count()

    # Calculate streak
    sessions = WorkoutSession.objects.filter(user=user).order_by('-completed_at')
    streak = 0
    previous_date = None
    for session in sessions:
        current_date = session.completed_at.date()
        if previous_date is None:
            streak = 1
            previous_date = current_date
        elif (previous_date - current_date).days == 1:
            streak += 1
            previous_date = current_date
        else:
            break

    # Add progress percentages to in-progress achievements
    in_progress_achievements_with_progress = []
    for achievement in in_progress_achievements:
        progress_percent = 0
        if achievement.criteria_value != 0:  # Avoid division by zero
            if achievement.criteria_type == 'run_count':
                progress_percent = (user_run_count / achievement.criteria_value) * 100
            elif achievement.criteria_type == 'gym_count':
                progress_percent = (user_gym_count / achievement.criteria_value) * 100
            elif achievement.criteria_type == 'total_distance':
                progress_percent = (total_distance / achievement.criteria_value) * 100
            elif achievement.criteria_type == 'total_volume':
                progress_percent = (total_volume / achievement.criteria_value) * 100
            elif achievement.criteria_type == 'streak':
                progress_percent = (streak / achievement.criteria_value) * 100
            elif achievement.criteria_type == 'total_workouts':
                progress_percent = (total_workouts / achievement.criteria_value) * 100
        progress_percent = min(progress_percent, 100)  # Cap at 100%
        in_progress_achievements_with_progress.append({
            'achievement': achievement,
            'progress_percent': round(progress_percent, 2)  # Round to 2 decimals
        })

    # Determine level title
    level_title = 'Novice' if 1 <= user.level <= 10 else 'Amateur' if 11 <= user.level <= 20 else 'Professional'

    context = {
        'earned_achievements': earned_achievements,
        'in_progress_achievements': in_progress_achievements_with_progress,
        'earned_achievements_count': earned_achievements_count,
        'user': user,
        'next_level_xp': next_level_xp,
        'xp_progress_percent': xp_progress_percent,
        'completion_percent': completion_percent,
        'user_run_count': user_run_count,
        'user_gym_count': user_gym_count,
        'total_distance': total_distance,
        'total_volume': total_volume,
        'total_workouts': total_workouts,
        'streak': streak,
        'level_title': level_title,
        'active_page': 'achievements',
    }
    return render(request, 'home/achievements.html', context)

def check_and_award_achievements(user):
    # Available achievements
    achievement_definitions = [
        {'name': 'First Mile Champion', 'description': 'Complete your first mile run', 'icon': '🏃', 'criteria_type': 'run_count', 'criteria_value': 1, 'xp_reward': 50},
        {'name': 'Power Warrior', 'description': 'Complete 10 strength workouts', 'icon': '💪', 'criteria_type': 'gym_count', 'criteria_value': 10, 'xp_reward': 500},
        {'name': 'Marathon Starter', 'description': 'Run a total of 42 km', 'icon': '🏅', 'criteria_type': 'total_distance', 'criteria_value': 42, 'xp_reward': 2100},
        {'name': 'Iron Lifter', 'description': 'Lift a total of 500,000 kg', 'icon': '🏋️', 'criteria_type': 'total_volume', 'criteria_value': 500000, 'xp_reward': 2000},
        {'name': 'Streak Starter', 'description': 'Work out 3 consecutive days', 'icon': '🔥', 'criteria_type': 'streak', 'criteria_value': 3, 'xp_reward': 150},
        {'name': 'Dedicated Athlete', 'description': 'Complete 50 workouts', 'icon': '⭐', 'criteria_type': 'total_workouts', 'criteria_value': 50, 'xp_reward': 2500},
    ]

    # Initialize or update achievements for the user
    for definition in achievement_definitions:
        achievement, created = Achievement.objects.get_or_create(
            user=user,
            name=definition['name'],
            defaults={
                'description': definition['description'],
                'icon': definition['icon'],
                'criteria_type': definition['criteria_type'],
                'criteria_value': definition['criteria_value'],
                'xp_reward': definition['xp_reward'],
            }
        )
        if not created:
            # Update existing achievement if definition changed
            achievement.description = definition['description']
            achievement.icon = definition['icon']
            achievement.criteria_type = definition['criteria_type']
            achievement.criteria_value = definition['criteria_value']
            achievement.xp_reward = definition['xp_reward']
            achievement.save()

    # Calculate metrics
    run_count = WorkoutSession.objects.filter(user=user, activity_type='R', distance__gte=1.609).count()
    gym_count = WorkoutSession.objects.filter(user=user, activity_type='G').count()
    total_distance = WorkoutSession.objects.filter(user=user, activity_type='R').aggregate(total=Sum('distance'))['total'] or 0
    total_volume = SessionSet.objects.filter(
        exercise__session__user=user,
        exercise__session__activity_type='G',
        completed=True,
        weight__gt=0,
        reps__gt=0
    ).aggregate(total=Sum(F('weight') * F('reps')))['total'] or 0
    total_workouts = WorkoutSession.objects.filter(user=user).count()

    # Calculate streak
    sessions = WorkoutSession.objects.filter(user=user).order_by('-completed_at')
    streak = 0
    previous_date = None
    for session in sessions:
        current_date = session.completed_at.date()
        if previous_date is None:
            streak = 1
            previous_date = current_date
        elif (previous_date - current_date).days == 1:
            streak += 1
            previous_date = current_date
        else:
            break

    # Check and award achievements
    for achievement in Achievement.objects.filter(user=user, earned_at__isnull=True):
        if achievement.criteria_type == 'run_count' and run_count >= achievement.criteria_value:
            achievement.earned_at = timezone.now()
            achievement.save()
            user.xp += achievement.xp_reward
        elif achievement.criteria_type == 'gym_count' and gym_count >= achievement.criteria_value:
            achievement.earned_at = timezone.now()
            achievement.save()
            user.xp += achievement.xp_reward
        elif achievement.criteria_type == 'total_distance' and total_distance >= achievement.criteria_value:
            achievement.earned_at = timezone.now()
            achievement.save()
            user.xp += achievement.xp_reward
        elif achievement.criteria_type == 'total_volume' and total_volume >= achievement.criteria_value:
            achievement.earned_at = timezone.now()
            achievement.save()
            user.xp += achievement.xp_reward
        elif achievement.criteria_type == 'streak' and streak >= achievement.criteria_value:
            achievement.earned_at = timezone.now()
            achievement.save()
            user.xp += achievement.xp_reward
        elif achievement.criteria_type == 'total_workouts' and total_workouts >= achievement.criteria_value:
            achievement.earned_at = timezone.now()
            achievement.save()
            user.xp += achievement.xp_reward

        # Update level
        user.level = max(1, math.floor(user.xp / 500) + 1)
        user.save()

openai.api_key = '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'

@login_required
def aicoach(request):
    return render(request, 'home/aicoach.html', {'active_page': 'aicoach'})

@login_required
@csrf_exempt
def aicoach_process(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message')

            # Gather user data
            user = request.user
            user_info = {
                'username': user.username,
                'fitness_level': user.get_fitness_level_display() or 'Unknown',
                'age': user.get_age() or 'Unknown',
                'weight': user.weight or 'Unknown',
                'height': user.height or 'Unknown',
                'gender': user.get_gender_display() or 'Unknown',
                'xp': user.xp,
                'level': user.level
            }

            # Gather workout data (last 7 days)
            week_start = timezone.now() - timedelta(days=7)
            recent_workouts = WorkoutSession.objects.filter(
                user=user,
                completed_at__gte=week_start
            )
            workout_count = recent_workouts.count()
            running_stats = recent_workouts.filter(activity_type='R').aggregate(
                total_distance=Sum('distance'),
                total_duration=Sum('duration_seconds')
            )
            running_distance = running_stats['total_distance'] or 0
            running_duration = running_stats['total_duration'] or 0
            running_pace = ((running_duration / 60) / running_distance) if running_distance > 0 else 0

            gym_volume = SessionSet.objects.filter(
                exercise__session__user=user,
                exercise__session__activity_type='G',
                exercise__session__completed_at__gte=week_start,
                completed=True
            ).aggregate(total_volume=Sum(F('weight') * F('reps')))['total_volume'] or 0

            # Recent exercises
            recent_exercises = SessionSet.objects.filter(
                exercise__session__user=user,
                exercise__session__activity_type='G',
                exercise__session__completed_at__gte=week_start,
                completed=True
            ).values('exercise__exercise_name').annotate(
                max_weight=Max('weight'),
                total_reps=Sum('reps')
            )

            # Goals
            goal = Goal.objects.filter(user=user).first()
            goal_workouts = goal.weekly_workouts if goal else 4
            goal_distance = goal.weekly_distance if goal else 20

            # Achievements
            earned_achievements = Achievement.objects.filter(user=user, earned_at__isnull=False).count()
            total_achievements = Achievement.objects.filter(user=user).count()

            # Prepare prompt with personality and user data
            prompt = f"""
You are FitTrack's AI Coach, a friendly, motivational, and supportive fitness assistant designed to inspire users of all levels (casual, beginner, professional). Your tone is encouraging, positive, and approachable, like a personal trainer who celebrates progress and provides practical advice. Use simple language to ensure clarity for all users. Tailor your responses to the user's fitness level, goals, and recent workout data. If asked for workout suggestions, provide specific exercises or routines based on their activity history and fitness level. If asked about their level, include their current level and XP progress. Always end your response with a motivational phrase and label it as AI-generated.

User Profile:
- Username: {user_info['username']}
- Fitness Level: {user_info['fitness_level']}
- Age: {user_info['age']}
- Weight: {user_info['weight']} kg
- Height: {user_info['height']} cm
- Gender: {user_info['gender']}
- Level: {user_info['level']} ({user_info['xp']} XP, {user_info['level'] * 500 - user_info['xp']} XP to next level)
- Achievements: {earned_achievements}/{total_achievements}

Recent Workout Data (last 7 days):
- Workouts Completed: {workout_count}
- Running: {running_distance:.1f} km, Pace: {running_pace:.2f} min/km
- Gym Volume: {gym_volume:.0f} kg
- Recent Gym Exercises: {', '.join([f"{ex['exercise__exercise_name']} ({ex['max_weight']} kg, {ex['total_reps']} reps)" for ex in recent_exercises]) or 'None'}

Goals:
- Weekly Workouts: {goal_workouts}
- Weekly Running Distance: {goal_distance} km

User Message: {user_message}

Provide a concise response (50-100 words) with specific, actionable advice or feedback. Avoid disclosing sensitive data unless relevant to the query.
"""

            # Send to ChatGPT
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a fitness coach providing personalized advice."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )

            ai_response = response.choices[0].message.content.strip()
            ai_response += "\n\n*AI-generated by FitTrack's AI Coach*"
            return JsonResponse({'status': 'success', 'response': ai_response})

        except openai.error.RateLimitError as e:
            # Return raw OpenAI message
            error_message = str(e)
            return JsonResponse({'status': 'error', 'response': error_message})
    return JsonResponse({'status': 'error', 'response': 'Invalid request method'})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("track"))
        else:
            return render(request, 'home/login.html', {'message': 'Invalid credentials'})
    return render(request, 'home/login.html')

def logout_view(request):
    logout(request)
    return render(request, 'home/login.html', {'message': 'Logged out.'})

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        birth_date = request.POST.get('birth_date') or None
        gender = request.POST.get('gender') or None
        weight = request.POST.get('weight') or None
        height = request.POST.get('height') or None
        fitness_level = request.POST.get('fitness_level') or None
        if CustomUser.objects.filter(username=username).exists():
            return render(request, 'home/register.html', {'message': 'Username already taken'})
        try:
            user = CustomUser.objects.create(
                username=username,
                password=make_password(password),
                birth_date=birth_date,
                gender=gender,
                weight=weight,
                height=height,
                fitness_level=fitness_level,
            )
            # Initialize achievements for new user
            achievement_definitions = [
                {'name': 'First Mile Champion', 'description': 'Complete your first mile run', 'icon': '🏃', 'criteria_type': 'run_count', 'criteria_value': 1, 'xp_reward': 50},
                {'name': 'Power Warrior', 'description': 'Complete 10 strength workouts', 'icon': '💪', 'criteria_type': 'gym_count', 'criteria_value': 10, 'xp_reward': 500},
                {'name': 'Marathon Starter', 'description': 'Run a total of 42 km', 'icon': '🏅', 'criteria_type': 'total_distance', 'criteria_value': 42, 'xp_reward': 2100},
                {'name': 'Iron Lifter', 'description': 'Lift a total of 500,000 kg', 'icon': '🏋️', 'criteria_type': 'total_volume', 'criteria_value': 500000, 'xp_reward': 2000},
                {'name': 'Streak Starter', 'description': 'Work out 3 consecutive days', 'icon': '🔥', 'criteria_type': 'streak', 'criteria_value': 3, 'xp_reward': 150},
                {'name': 'Dedicated Athlete', 'description': 'Complete 50 workouts', 'icon': '⭐', 'criteria_type': 'total_workouts', 'criteria_value': 50, 'xp_reward': 2500},
            ]
            for definition in achievement_definitions:
                Achievement.objects.get_or_create(
                    user=user,
                    name=definition['name'],
                    defaults={
                        'description': definition['description'],
                        'icon': definition['icon'],
                        'criteria_type': definition['criteria_type'],
                        'criteria_value': definition['criteria_value'],
                        'xp_reward': definition['xp_reward'],
                    }
                )
            login(request, user)
            return HttpResponseRedirect(reverse("track"))
        except Exception as e:
            return render(request, 'home/register.html', {'message': str(e)})
    return render(request, 'home/register.html')

def get_workout_form(request):
    return render(request, 'home/workout-form.html')


@login_required
def create_template(request):

    if request.method == 'POST':

        name = request.POST.get('name')
        activity_type = request.POST.get('activity_type')

        if not name or not activity_type:

            return render(request, 'create_template.html', {'error': 'Name and activity type are required'})

        template = WorkoutTemplate.objects.create(
            user=request.user,
            name=name,
            activity_type=activity_type,
        )


        if activity_type == 'R':
            template.distance = float(request.POST.get('distance', 0) or 0)
            template.pace = request.POST.get('pace')
            template.save()

        elif activity_type == 'G':
            # Collect all exercise names and sets
            exercise_data = {}
            for key in request.POST:
                if key.startswith('exercise_') and '_name' in key:
                    exercise_id = key.split('_')[1]
                    exercise_name = request.POST.get(key)
                    if exercise_name:
                        exercise_data[exercise_id] = {'name': exercise_name, 'sets': {}}
                elif key.startswith('exercise_') and '_set_' in key:
                    parts = key.split('_')
                    exercise_id, set_number = parts[1], parts[3]
                    if exercise_id in exercise_data:
                        if 'reps' in key:
                            exercise_data[exercise_id]['sets'].setdefault(set_number, {})['reps'] = request.POST.get(key)
                        elif 'weight' in key:
                            exercise_data[exercise_id]['sets'].setdefault(set_number, {})['weight'] = request.POST.get(key)

            # Create exercises and sets
            for exercise_id, data in exercise_data.items():
                exercise = GymExercise.objects.create(
                    template=template,
                    exercise_name=data['name'],
                )

                for set_number, set_data in data['sets'].items():
                    try:
                        reps = int(set_data.get('reps', 0) or 0)
                        weight = float(set_data.get('weight', 0) or 0) if set_data.get('weight') else None
                        if reps > 0:
                            ExerciseSet.objects.create(
                                exercise=exercise,
                                set_number=int(set_number),
                                reps=reps,
                                weight=weight,
                            )

                    except ValueError as e:

                        continue
        return HttpResponseRedirect(reverse("track"))
    return render(request, 'home/track.html')

@login_required
def start_run(request, template_id):
    template = get_object_or_404(WorkoutTemplate, id=template_id, user=request.user, activity_type='R')
    recent_session = WorkoutSession.objects.filter(
        user=request.user,
        template=template,
        activity_type='R'
    ).order_by('-completed_at').first()

    distance = recent_session.distance if recent_session else template.distance
    previous_distance = recent_session.distance if recent_session else None
    previous_pace = recent_session.get_pace() if recent_session else None
    previous_duration = recent_session.get_duration_display() if recent_session else None

    workout_data = {
        'title': template.name,
        'template_id': template.id,
        'template_distance': template.distance if template.distance is not None else "",
        'exercises': [{
            'name': "Distance Tracking",
            'sets': [{
                'previous': f"{previous_distance} km, Pace: {previous_pace or 'N/A'}, Duration: {previous_duration or 'N/A'}",
                'distance': distance if distance is not None else ""
            }]
        }]
    }
    context = {
        'template': template,
        'speed': template.get_speed(),
        'duration': template.get_duration_display(),
        'workout_data_json': json.dumps(workout_data, cls=DjangoJSONEncoder),
    }
    return render(request, 'home/workout-session.html', context)

@login_required
def start_gym(request, template_id):
    template = get_object_or_404(WorkoutTemplate, id=template_id, user=request.user, activity_type='G')
    recent_session = WorkoutSession.objects.filter(
        user=request.user,
        template=template,
        activity_type='G'
    ).order_by('-completed_at').first()

    exercises = []
    for exercise in template.exercises.all():
        sets = []
        if recent_session:
            last_session_exercise = SessionExercise.objects.filter(
                session=recent_session,
                exercise_name=exercise.exercise_name
            ).first()
            template_sets = {set.set_number: set for set in exercise.sets.order_by('set_number')}
            completed_sets = {set.set_number: set for set in last_session_exercise.sets.all()} if last_session_exercise else {}
            for set_number, set in template_sets.items():
                previous = "Not Done"
                if set_number in completed_sets:
                    last_set = completed_sets[set_number]
                    previous = f"{last_set.weight}kg x {last_set.reps}" if last_set.weight else f"{last_set.reps} reps"

                sets.append({
                    'previous': previous,
                    'weight': set.weight if set.weight is not None else "",
                    'reps': set.reps if set.reps is not None else "",
                    'completed': False  # Always start unchecked
                })
        else:
            sets = [
                {
                    'previous': f"{set.weight}kg x {set.reps}" if set.weight else f"{set.reps} reps",
                    'weight': set.weight if set.weight is not None else "",
                    'reps': set.reps if set.reps is not None else "",
                    'completed': False
                }
                for set in exercise.sets.order_by('set_number')
            ]
        exercises.append({
            'name': exercise.exercise_name,
            'sets': sets
        })

    workout_data = {
        'title': template.name,
        'template_id': template.id,
        'exercises': exercises
    }
    context = {
        'template': template,
        'exercise_count': template.get_exercise_count(),
        'workout_data_json': json.dumps(workout_data, cls=DjangoJSONEncoder),
    }
    return render(request, 'home/workout-session.html', context)

@login_required
def delete_template(request, template_id):
    template = get_object_or_404(WorkoutTemplate, id=template_id, user=request.user)
    if request.method == 'POST':
        template_name = template.name
        template.delete()
        return HttpResponseRedirect(reverse("track"))
    return HttpResponseRedirect(reverse("track"))

@login_required
def finish_workout(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            template_id = data.get('template_id')
            activity_type = data.get('activity_type')
            distance = data.get('distance')
            duration_seconds = data.get('duration_seconds')
            exercises = data.get('exercises', [])

            template = get_object_or_404(WorkoutTemplate, id=template_id, user=request.user)
            if activity_type != template.activity_type:
                return JsonResponse({'status': 'error', 'message': 'Activity type mismatch'}, status=400)

            session = WorkoutSession.objects.create(
                user=request.user,
                template=template,
                activity_type=activity_type,
                distance=float(distance) if distance is not None else None,
                duration_seconds=int(duration_seconds) if duration_seconds is not None else None,
                completed_at=timezone.now()
            )

            if activity_type == 'G' and exercises:
                # Update template with current structure
                template.exercises.all().delete()
                for idx, exercise_data in enumerate(exercises):
                    gym_exercise = GymExercise.objects.create(
                        template=template,
                        exercise_name=exercise_data['name'],
                    )
                    for set_idx, set_data in enumerate(exercise_data['sets']):
                        try:
                            reps = int(set_data['reps']) if set_data['reps'] not in [None, ""] else None
                            weight = float(set_data['weight']) if set_data['weight'] not in [None, ""] else None
                            ExerciseSet.objects.create(
                                exercise=gym_exercise,
                                set_number=set_idx + 1,
                                reps=reps,
                                weight=weight,
                            )
                        except (ValueError, TypeError) as e:
                            print(f"Error creating ExerciseSet: {e}")

                # Save completed sets for history
                SessionExercise.objects.filter(session=session).delete()
                for idx, exercise_data in enumerate(exercises):
                    completed_sets = [s for s in exercise_data['sets'] if s.get('completed')]
                    if completed_sets:
                        session_exercise = SessionExercise.objects.create(
                            session=session,
                            exercise_name=exercise_data['name'],
                            order=idx + 1,
                        )
                        for set_idx, set_data in enumerate(exercise_data['sets']):
                            if set_data.get('completed'):
                                try:
                                    reps = int(set_data['reps']) if set_data['reps'] not in [None, ""] else None
                                    weight = float(set_data['weight']) if set_data['weight'] not in [None, ""] else None
                                    SessionSet.objects.create(
                                        exercise=session_exercise,
                                        set_number=set_idx + 1,
                                        reps=reps,
                                        weight=weight,
                                        completed=True  # Set completed field
                                    )
                                    print(f"Saved SessionSet: {session_exercise.exercise_name}, Set {set_idx + 1}, {weight}kg x {reps}")
                                except (ValueError, TypeError) as e:
                                    print(f"Error creating SessionSet: {e}")

            # Award XP: 50 per workout, +50 for runs
            user = request.user
            user.xp += 50
            if activity_type == 'R':
                user.xp += 50
            user.level = max(1, math.floor(user.xp / 500) + 1)
            user.save()

            # Check and award achievements
            check_and_award_achievements(request.user)

            return JsonResponse({'status': 'success', 'redirect_url': reverse('track')})
        except (ValueError, TypeError, KeyError) as e:

            return JsonResponse({'status': 'error', 'message': 'Invalid data'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)