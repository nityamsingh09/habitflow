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

from .models import ChallengeInvite

class InviteInline(admin.TabularInline):
    model  = ChallengeInvite
    extra  = 0
    readonly_fields = ('invited_by','invited_user','invited_email','status','created_at')

# Re-register Challenge with invite inline
admin.site.unregister(Challenge)
@admin.register(Challenge)
class ChallengeAdminV2(admin.ModelAdmin):
    list_display  = ('title','creator','habit_name','start_date','end_date','status_display','participant_count')
    list_filter   = ('is_public',)
    search_fields = ('title','creator__email','habit_name')
    inlines       = [ParticipantInline, InviteInline]
    def status_display(self, obj): return obj.status
    def participant_count(self, obj): return obj.participants.count()
    status_display.short_description   = 'Status'
    participant_count.short_description = 'Participants'

@admin.register(ChallengeInvite)
class ChallengeInviteAdmin(admin.ModelAdmin):
    list_display  = ('challenge','invited_user','invited_by','status','created_at')
    list_filter   = ('status',)
    search_fields = ('challenge__title','invited_user__email','invited_by__email')
