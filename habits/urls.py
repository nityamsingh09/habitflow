from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),

    path('api/habits', views.habits, name='habits'),
    path('api/habits/<str:habit_id>', views.habit_detail, name='habit_detail'),

    path('api/log', views.log_habit, name='log_habit'),
    path('api/logs', views.get_logs, name='get_logs'),

    path('api/stats', views.get_stats, name='get_stats'),
    path('api/today', views.get_today, name='get_today'),

    path('api/badges', views.get_badges, name='get_badges'),
    path('api/badge-definitions', views.get_badge_definitions, name='badge_definitions'),

    path('api/me', views.get_me, name='get_me'),
]
