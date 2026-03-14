from django.urls import path
from . import views

urlpatterns = [
    path('api/xp',               views.my_xp,           name='my_xp'),
    path('api/quests',           views.daily_quests,    name='daily_quests'),
    path('api/quests/check',     views.daily_quests,    name='check_quests'),
    path('api/freeze/use',       views.use_streak_freeze, name='use_freeze'),
    path('api/freeze/buy',       views.buy_streak_freeze, name='buy_freeze'),
    path('api/mood',             views.mood,             name='mood'),
    path('api/insights',         views.weekly_insights,  name='insights'),
    path('api/habit-templates',  views.habit_templates,  name='habit_templates'),
]
