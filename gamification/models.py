from django.conf import settings
from django.db import models
from django.utils import timezone


# ── XP Config ─────────────────────────────────────────────────────────────
XP_PER_LOG        = 10
XP_STREAK_BONUS   = {7: 50, 14: 100, 21: 150, 30: 300, 60: 600, 100: 1000}
XP_BADGE_BONUS    = 200
XP_CHALLENGE_WIN  = 500
XP_DAILY_QUEST    = 30

LEVELS = [
    (0,    'Seedling',   '🌱', '#6ee7b7'),
    (100,  'Sprout',     '🌿', '#34d399'),
    (300,  'Grower',     '🌳', '#10b981'),
    (600,  'Achiever',   '⚡', '#c8ff00'),
    (1000, 'Warrior',    '🔥', '#f97316'),
    (2000, 'Champion',   '💎', '#60a5fa'),
    (4000, 'Master',     '🏆', '#a78bfa'),
    (7000, 'Grandmaster','🛡️', '#fbbf24'),
    (12000,'Legend',     '🌟', '#ff6b6b'),
]

def get_level(xp):
    level_idx = 0
    for i, (threshold, *_) in enumerate(LEVELS):
        if xp >= threshold:
            level_idx = i
    lvl = LEVELS[level_idx]
    next_lvl = LEVELS[level_idx + 1] if level_idx + 1 < len(LEVELS) else None
    progress = 0
    if next_lvl:
        span = next_lvl[0] - lvl[0]
        earned = xp - lvl[0]
        progress = min(100, int(earned / span * 100))
    return {
        'index':      level_idx,
        'name':       lvl[1],
        'emoji':      lvl[2],
        'color':      lvl[3],
        'xp':         xp,
        'threshold':  lvl[0],
        'next_threshold': next_lvl[0] if next_lvl else None,
        'next_name':  next_lvl[1] if next_lvl else 'Max Level',
        'progress':   progress,
    }


class UserXP(models.Model):
    user       = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                      related_name='xp')
    total_xp   = models.PositiveIntegerField(default=0)
    streak_freezes = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def level_info(self):
        return get_level(self.total_xp)

    def add_xp(self, amount, reason=''):
        self.total_xp += amount
        self.save(update_fields=['total_xp', 'updated_at'])
        XPTransaction.objects.create(user=self.user, amount=amount, reason=reason)
        return self.total_xp

    def __str__(self):
        return f"{self.user.email} — {self.total_xp} XP"


class XPTransaction(models.Model):
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='xp_transactions')
    amount     = models.IntegerField()
    reason     = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


QUEST_TYPES = [
    ('log_3',     'Log 3 habits today',              30),
    ('log_5',     'Log 5 habits today',              60),
    ('log_all',   'Complete all habits today',       100),
    ('streak_any','Keep any streak alive today',     30),
    ('social',    'React to a friend\'s activity',   20),
]

class DailyQuest(models.Model):
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name='daily_quests')
    quest_type  = models.CharField(max_length=30)
    quest_date  = models.DateField()
    completed   = models.BooleanField(default=False)
    xp_reward   = models.PositiveIntegerField(default=30)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'quest_type', 'quest_date')

    def to_dict(self):
        defn = next((q for q in QUEST_TYPES if q[0] == self.quest_type), None)
        return {
            'id':          self.id,
            'type':        self.quest_type,
            'label':       defn[1] if defn else self.quest_type,
            'xp_reward':   self.xp_reward,
            'completed':   self.completed,
            'completed_at': str(self.completed_at) if self.completed_at else None,
        }


class StreakFreeze(models.Model):
    """Records when a user spent a freeze token."""
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                   related_name='freezes_used')
    habit      = models.ForeignKey('habits.Habit', on_delete=models.CASCADE,
                                   related_name='freezes')
    freeze_date = models.DateField()
    used_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('habit', 'freeze_date')


class MoodLog(models.Model):
    user      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name='mood_logs')
    log_date  = models.DateField()
    mood      = models.PositiveSmallIntegerField()  # 1–5
    note      = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'log_date')

    LABELS = {1: '😞 Rough', 2: '😕 Meh', 3: '😐 Okay', 4: '😊 Good', 5: '🤩 Amazing'}

    def to_dict(self):
        return {
            'date':  str(self.log_date),
            'mood':  self.mood,
            'label': self.LABELS.get(self.mood, ''),
            'note':  self.note,
        }
