from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import date, timedelta


class Challenge(models.Model):
    STATUS_ACTIVE   = 'active'
    STATUS_COMPLETE = 'complete'
    STATUS_EXPIRED  = 'expired'

    creator      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='created_challenges')
    title        = models.CharField(max_length=100)
    description  = models.CharField(max_length=300, blank=True)
    habit_name   = models.CharField(max_length=100)
    habit_icon   = models.CharField(max_length=10, default='🎯')
    duration_days = models.PositiveIntegerField(default=7)
    start_date   = models.DateField()
    end_date     = models.DateField()
    is_public    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    @property
    def status(self):
        today = date.today()
        if today > self.end_date:
            return self.STATUS_EXPIRED if not self._has_winner() else self.STATUS_COMPLETE
        return self.STATUS_ACTIVE

    def _has_winner(self):
        return self.participants.filter(completed=True).exists()

    def to_dict(self, user=None):
        participants = self.participants.select_related('user').all()
        part_list = []
        for p in participants:
            part_list.append({
                'user_id':      str(p.user.id),
                'display_name': p.user.display_name,
                'avatar_url':   p.user.avatar_url,
                'logs':         p.log_count,
                'completed':    p.completed,
                'is_me':        user and p.user == user,
            })
        part_list.sort(key=lambda x: x['logs'], reverse=True)
        my_part = next((p for p in participants if user and p.user == user), None)
        return {
            'id':             self.id,
            'title':          self.title,
            'description':    self.description,
            'habit_name':     self.habit_name,
            'habit_icon':     self.habit_icon,
            'duration_days':  self.duration_days,
            'start_date':     str(self.start_date),
            'end_date':       str(self.end_date),
            'days_left':      max(0, (self.end_date - date.today()).days),
            'status':         self.status,
            'is_public':      self.is_public,
            'participant_count': participants.count(),
            'participants':   part_list,
            'im_in':          my_part is not None,
            'my_logs':        my_part.log_count if my_part else 0,
        }

    def __str__(self):
        return self.title


class ChallengeParticipant(models.Model):
    challenge  = models.ForeignKey(Challenge, on_delete=models.CASCADE,
                                   related_name='participants')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='challenge_participations')
    joined_at  = models.DateTimeField(auto_now_add=True)
    completed  = models.BooleanField(default=False)

    class Meta:
        unique_together = ('challenge', 'user')

    @property
    def log_count(self):
        return ChallengeLog.objects.filter(participant=self).count()


class ChallengeLog(models.Model):
    participant = models.ForeignKey(ChallengeParticipant, on_delete=models.CASCADE,
                                    related_name='logs')
    log_date    = models.DateField()
    logged_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('participant', 'log_date')


class ChallengeInvite(models.Model):
    STATUS_PENDING  = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_DECLINED = 'declined'
    STATUS_CHOICES  = [('pending','Pending'),('accepted','Accepted'),('declined','Declined')]

    challenge   = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='invites')
    invited_by  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invites')
    invited_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='received_invites', null=True, blank=True)
    invited_email = models.EmailField(blank=True)   # fallback if user not found yet
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at  = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('challenge', 'invited_user')

    def to_dict(self):
        return {
            'id':           self.id,
            'challenge_id': self.challenge_id,
            'challenge_title': self.challenge.title,
            'challenge_icon':  self.challenge.habit_icon,
            'invited_by':   self.invited_by.display_name,
            'status':       self.status,
            'created_at':   str(self.created_at),
        }
