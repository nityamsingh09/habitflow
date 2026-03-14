from django.contrib import admin
from .models import Challenge, ChallengeParticipant, ChallengeLog

class ParticipantInline(admin.TabularInline):
    model = ChallengeParticipant
    extra = 0
    readonly_fields = ('user','joined_at','completed')

@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display  = ('title','creator','habit_name','start_date','end_date','status','participant_count')
    list_filter   = ('is_public',)
    search_fields = ('title','creator__email','habit_name')
    inlines       = [ParticipantInline]
    def status(self, obj): return obj.status
    def participant_count(self, obj): return obj.participants.count()
    participant_count.short_description = 'Participants'

@admin.register(ChallengeParticipant)
class ChallengeParticipantAdmin(admin.ModelAdmin):
    list_display = ('user','challenge','completed','log_count','joined_at')
    def log_count(self, obj): return obj.log_count
    log_count.short_description = 'Logs'
