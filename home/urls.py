from django.urls import path
from . import views

urlpatterns = [
    path("track/", views.track, name="track"),
    path("analytics", views.analytics, name="analytics"),
    path("achievements", views.achievements, name="achievements"),
    path("aicoach", views.aicoach, name="aicoach"),
    path("aicoach_process/", views.aicoach_process, name="aicoach_process"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path('get-workout-form/', views.get_workout_form, name='get_workout_form'),
    path('create-template/', views.create_template, name='create-template'),
    # path('start-workout/', views.start_workout, name='start-workout'),
    path('start-run/<int:template_id>/', views.start_run, name='start_run'),
    path('start-gym/<int:template_id>/', views.start_gym, name='start_gym'),
    path('delete-template/<int:template_id>/', views.delete_template, name='delete_template'),
    path('finish-workout/', views.finish_workout, name='finish_workout'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('update-goals/', views.update_goals, name='update_goals'),
]