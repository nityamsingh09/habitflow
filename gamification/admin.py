from django.contrib import admin
from .models import UserXP, XPTransaction, DailyQuest, StreakFreeze, MoodLog

@admin.register(UserXP)
class UserXPAdmin(admin.ModelAdmin):
    list_display  = ('user','total_xp','level_name','streak_freezes','updated_at')
    search_fields = ('user__email',)
    ordering      = ('-total_xp',)
    def level_name(self, obj):
        i = obj.level_info()
        return f"{i['emoji']} {i['name']}"
    level_name.short_description = 'Level'

@admin.register(XPTransaction)
class XPTransactionAdmin(admin.ModelAdmin):
    list_display  = ('user','amount','reason','created_at')
    list_filter   = ('created_at',)
    search_fields = ('user__email','reason')
    ordering      = ('-created_at',)

@admin.register(DailyQuest)
class DailyQuestAdmin(admin.ModelAdmin):
    list_display  = ('user','quest_type','quest_date','completed','xp_reward')
    list_filter   = ('completed','quest_date','quest_type')
    search_fields = ('user__email',)
    date_hierarchy = 'quest_date'

@admin.register(StreakFreeze)
class StreakFreezeAdmin(admin.ModelAdmin):
    list_display  = ('user','habit','freeze_date','used_at')
    search_fields = ('user__email','habit__name')

@admin.register(MoodLog)
class MoodLogAdmin(admin.ModelAdmin):
    list_display  = ('user','log_date','mood_emoji','note')
    list_filter   = ('mood','log_date')
    search_fields = ('user__email',)
    date_hierarchy = 'log_date'
    def mood_emoji(self, obj):
        return {1:'😞',2:'😕',3:'😐',4:'😊',5:'🤩'}.get(obj.mood,'❓') + f' {obj.mood}/5'
    mood_emoji.short_description = 'Mood'
