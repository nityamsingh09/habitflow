from django.contrib import admin
from django.urls import path, include
from django.conf import settings

admin.site.site_header = 'HabitFlows Admin'
admin.site.site_title  = 'HabitFlows'
admin.site.index_title = '📊 Dashboard'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('habits.urls')),
    path('', include('social.urls')),
    path('auth/', include('accounts.urls')),
    path('', include('gamification.urls')),
    path('', include('challenges.urls')),
]
