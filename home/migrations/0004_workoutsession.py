# Generated by Django 5.1.7 on 2025-03-28 17:04

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_gymexercise_exerciseset_workouttemplate_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkoutSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_type', models.CharField(choices=[('R', 'Running'), ('G', 'Gym Session')], max_length=1)),
                ('distance', models.FloatField(blank=True, help_text='Distance in kilometers', null=True)),
                ('duration_seconds', models.IntegerField(blank=True, help_text='Duration in seconds', null=True)),
                ('completed_at', models.DateTimeField(auto_now_add=True)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to='home.workouttemplate')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
