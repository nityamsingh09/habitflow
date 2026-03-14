from django.contrib import admin
from .models import Subscription

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display  = ('user','plan','is_premium_display','expires_at','updated_at')
    list_filter   = ('plan','is_active')
    search_fields = ('user__email',)
    ordering      = ('-updated_at',)
    def is_premium_display(self, obj):
        return '✅ Premium' if obj.is_premium else '🆓 Free'
    is_premium_display.short_description = 'Status'
