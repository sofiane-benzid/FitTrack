from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    CustomUser, WorkoutTemplate, GymExercise, ExerciseSet,
    WorkoutSession, SessionExercise, SessionSet
)

# CustomUser Admin
class CustomUserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {
            'fields': (
                'first_name', 'last_name', 'email', 'birth_date',
                'gender', 'weight', 'height', 'fitness_level'
            ),
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined'),
        }),
    )
    list_display = (
        'username', 'email', 'gender', 'weight', 'height', 'fitness_level', 'get_age', 'is_staff'
    )

    def get_age(self, obj):
        return obj.get_age()
    get_age.short_description = 'Age'

# Inlines
class GymExerciseInline(admin.TabularInline):
    model = GymExercise
    extra = 1

class ExerciseSetInline(admin.TabularInline):
    model = ExerciseSet
    extra = 1

class SessionExerciseInline(admin.TabularInline):
    model = SessionExercise
    extra = 0  # No extra rows since these are completed sets

class SessionSetInline(admin.TabularInline):
    model = SessionSet
    extra = 0

# WorkoutTemplate Admin
class WorkoutTemplateAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'activity_type_display', 'created_at', 'last_session_date')
    list_filter = ('activity_type', 'user')
    search_fields = ('name', 'user__username')
    inlines = [GymExerciseInline]

    def activity_type_display(self, obj):
        return obj.get_activity_type_display()
    activity_type_display.short_description = 'Activity Type'

    def last_session_date(self, obj):
        last_session = obj.sessions.order_by('-completed_at').first()
        return last_session.completed_at if last_session else "No sessions"
    last_session_date.short_description = 'Last Session'

# GymExercise Admin
class GymExerciseAdmin(admin.ModelAdmin):
    list_display = ('id', 'exercise_name', 'template', 'set_count', 'last_completed')
    list_filter = ('template__user', 'template__activity_type')
    search_fields = ('exercise_name', 'template__name')
    inlines = [ExerciseSetInline]

    def set_count(self, obj):
        return obj.sets.count()
    set_count.short_description = 'Sets'

    def last_completed(self, obj):
        last_session = WorkoutSession.objects.filter(template=obj.template).order_by('-completed_at').first()
        if last_session:
            last_exercise = SessionExercise.objects.filter(
                session=last_session,
                exercise_name=obj.exercise_name
            ).first()
            return last_exercise.sets.count() if last_exercise else "Not completed"
        return "No sessions"
    last_completed.short_description = 'Last Completed Sets'

# ExerciseSet Admin
class ExerciseSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'exercise', 'set_number', 'reps', 'weight')
    list_filter = ('exercise__template__user',)
    search_fields = ('exercise__exercise_name',)

# WorkoutSession Admin
class WorkoutSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'template', 'activity_type_display', 'completed_at', 'duration_display')
    list_filter = ('activity_type', 'user', 'completed_at')
    search_fields = ('template__name', 'user__username')
    inlines = [SessionExerciseInline]

    fields = ('user', 'template', 'activity_type', 'distance', 'duration_seconds', 'completed_at')

    def activity_type_display(self, obj):
        return obj.get_activity_type_display()
    activity_type_display.short_description = 'Activity Type'

    def duration_display(self, obj):
        return obj.get_duration_display()
    duration_display.short_description = 'Duration'

# SessionExercise Admin
class SessionExerciseAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'exercise_name', 'order', 'set_count')
    list_filter = ('session__user', 'session__completed_at')
    search_fields = ('exercise_name', 'session__template__name')
    inlines = [SessionSetInline]

    def set_count(self, obj):
        return obj.sets.count()
    set_count.short_description = 'Completed Sets'

# SessionSet Admin
class SessionSetAdmin(admin.ModelAdmin):
    list_display = ('id', 'exercise', 'set_number', 'reps', 'weight')
    list_filter = ('exercise__session__user', 'exercise__session__completed_at')
    search_fields = ('exercise__exercise_name',)

# Register all models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(WorkoutTemplate, WorkoutTemplateAdmin)
admin.site.register(GymExercise, GymExerciseAdmin)
admin.site.register(ExerciseSet, ExerciseSetAdmin)
admin.site.register(WorkoutSession, WorkoutSessionAdmin)
admin.site.register(SessionExercise, SessionExerciseAdmin)
admin.site.register(SessionSet, SessionSetAdmin)