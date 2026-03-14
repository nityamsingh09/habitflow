import uuid
from django.conf import settings
from django.db import models
from datetime import date


class Habit(models.Model):
    habit_id     = models.CharField(max_length=100, unique=True)
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='habits', null=True, blank=True)
    name         = models.CharField(max_length=200)
    icon         = models.CharField(max_length=20, default='⭐')
    category     = models.CharField(max_length=100, default='General')
    color        = models.CharField(max_length=20, default='#c8ff00')
    is_default   = models.BooleanField(default=False)
    is_public    = models.BooleanField(default=True)
    target_days  = models.PositiveIntegerField(null=True, blank=True)
    target_start = models.DateField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            "id":           self.habit_id,
            "name":         self.name,
            "icon":         self.icon,
            "category":     self.category,
            "color":        self.color,
            "target_days":  self.target_days,
            "target_start": str(self.target_start) if self.target_start else None,
            "is_public":    self.is_public,
        }

    def __str__(self):
        return self.name


class HabitLog(models.Model):
    habit    = models.ForeignKey(Habit, on_delete=models.CASCADE,
                                 related_name='logs', to_field='habit_id')
    log_date = models.DateField()

    class Meta:
        unique_together = ('habit', 'log_date')

    def __str__(self):
        return f"{self.habit.name} — {self.log_date}"


BADGE_DEFINITIONS = [
    ("target_complete", "Goal Crusher",   "🏆", "Completed a habit within its target days",         "target_complete", 1),
    ("target_early",    "Early Bird",     "⚡", "Finished target 10+ days before the deadline",     "target_early",    10),
    ("target_perfect",  "Flawless",       "💎", "Hit every single day of a target without missing", "target_perfect",  1),
    ("streak_7",        "Week Warrior",   "🔥", "7-day streak on any habit",                        "streak",          7),
    ("streak_21",       "Habit Formed",   "🧠", "21-day streak — the classic habit-forming mark",   "streak",          21),
    ("streak_30",       "Iron Will",      "⚙️", "30-day streak on any habit",                       "streak",          30),
    ("streak_60",       "Diamond Streak", "💠", "60-day streak on any habit",                       "streak",          60),
    ("streak_100",      "Centurion",      "🛡️", "100-day streak on any habit",                      "streak",          100),
    ("total_10",        "Getting Started","🌱", "10 total completions on a single habit",           "total",           10),
    ("total_50",        "Consistent",     "📈", "50 total completions on a single habit",           "total",           50),
    ("total_100",       "Triple Digits",  "💯", "100 total completions on a single habit",          "total",           100),
    ("total_365",       "Year Strong",    "🌟", "365 total completions on a single habit",          "total",           365),
    ("multi_target",    "Goal Collector", "🎯", "Completed 3 or more targets",                      "multi_target",    3),
]


class Badge(models.Model):
    badge_id   = models.CharField(max_length=60)
    habit      = models.ForeignKey(Habit, on_delete=models.CASCADE,
                                   related_name='badges', to_field='habit_id')
    earned_at  = models.DateField(default=date.today)
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('badge_id', 'habit')

    def to_dict(self):
        defn = next((b for b in BADGE_DEFINITIONS if b[0] == self.badge_id), None)
        return {
            "badge_id":    self.badge_id,
            "habit_id":    self.habit.habit_id,
            "habit_name":  self.habit.name,
            "habit_icon":  self.habit.icon,
            "habit_color": self.habit.color,
            "name":        defn[1] if defn else self.badge_id,
            "emoji":       defn[2] if defn else "🏅",
            "description": defn[3] if defn else "",
            "earned_at":   str(self.earned_at),
            "extra_data":  self.extra_data,
        }

    def __str__(self):
        return f"{self.badge_id} — {self.habit.name}"

# Migration 0002 adds is_public field to Habit (done via migration file)
