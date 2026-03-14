from django.conf import settings
from django.db import models
from django.utils.text import slugify


class UserProfile(models.Model):
    user       = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                      related_name='profile')
    username   = models.CharField(max_length=40, unique=True, blank=True)
    bio        = models.CharField(max_length=200, blank=True)
    is_public  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.username:
            base = slugify(self.user.display_name or self.user.email.split('@')[0])
            base = base[:30] or 'user'
            candidate, n = base, 1
            while UserProfile.objects.filter(username=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}{n}"; n += 1
            self.username = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"@{self.username}"


class Follow(models.Model):
    """One-way follow — no approval needed."""
    follower   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='following')
    following  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower} follows {self.following}"


class FriendRequest(models.Model):
    STATUS_PENDING  = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_DECLINED = 'declined'
    STATUS_CHOICES  = [(STATUS_PENDING,'Pending'),(STATUS_ACCEPTED,'Accepted'),(STATUS_DECLINED,'Declined')]

    from_user  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='sent_requests')
    to_user    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='received_requests')
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('from_user', 'to_user')


class ActivityEvent(models.Model):
    TYPE_LOG    = 'log'
    TYPE_STREAK = 'streak'
    TYPE_BADGE  = 'badge'
    TYPE_TARGET = 'target'
    TYPE_CHOICES = [
        (TYPE_LOG,    'Habit Logged'),
        (TYPE_STREAK, 'Streak Milestone'),
        (TYPE_BADGE,  'Badge Earned'),
        (TYPE_TARGET, 'Target Completed'),
    ]
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='activity_events')
    habit      = models.ForeignKey('habits.Habit', on_delete=models.CASCADE,
                                   related_name='activity_events', null=True, blank=True)
    event_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    meta       = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


REACTIONS = ['🔥','💪','🎉','❤️','⚡']


class Reaction(models.Model):
    event      = models.ForeignKey(ActivityEvent, on_delete=models.CASCADE, related_name='reactions')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='reactions')
    emoji      = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user', 'emoji')


class Comment(models.Model):
    event      = models.ForeignKey(ActivityEvent, on_delete=models.CASCADE, related_name='comments')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='comments')
    text       = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def to_dict(self):
        profile_username = ''
        try:
            profile_username = self.user.profile.username
        except Exception:
            pass
        return {
            'id':           self.id,
            'user_id':      str(self.user.id),
            'display_name': self.user.display_name,
            'avatar_url':   self.user.avatar_url,
            'username':     profile_username,
            'text':         self.text,
            'created_at':   self.created_at.strftime('%b %d · %H:%M'),
        }


def are_friends(user_a, user_b):
    return FriendRequest.objects.filter(
        status=FriendRequest.STATUS_ACCEPTED
    ).filter(
        models.Q(from_user=user_a, to_user=user_b) |
        models.Q(from_user=user_b, to_user=user_a)
    ).exists()


def get_friends(user):
    accepted = FriendRequest.objects.filter(
        status=FriendRequest.STATUS_ACCEPTED
    ).filter(
        models.Q(from_user=user) | models.Q(to_user=user)
    ).select_related('from_user__profile', 'to_user__profile')
    return [fr.to_user if fr.from_user == user else fr.from_user for fr in accepted]


def is_following(follower, following):
    return Follow.objects.filter(follower=follower, following=following).exists()


# ── CHAT MODELS ────────────────────────────────────────────────────────────

class GlobalMessage(models.Model):
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='global_messages')
    text       = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def to_dict(self):
        username = ''
        try: username = self.user.profile.username
        except: pass
        return {
            'id':           self.id,
            'user_id':      str(self.user.id),
            'display_name': self.user.display_name,
            'username':     username,
            'avatar_url':   self.user.avatar_url,
            'text':         self.text,
            'created_at':   self.created_at.strftime('%b %d · %H:%M'),
            'ts':           self.created_at.timestamp(),
        }


class DirectMessage(models.Model):
    sender     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='sent_dms')
    recipient  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='received_dms')
    text       = models.CharField(max_length=500)
    read       = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def to_dict(self, me=None):
        return {
            'id':           self.id,
            'sender_id':    str(self.sender.id),
            'sender_name':  self.sender.display_name,
            'sender_av':    self.sender.avatar_url,
            'text':         self.text,
            'is_me':        me and self.sender == me,
            'read':         self.read,
            'created_at':   self.created_at.strftime('%H:%M'),
            'ts':           self.created_at.timestamp(),
        }
