from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Subscription(models.Model):
    PLAN_FREE    = 'free'
    PLAN_MONTHLY = 'monthly'
    PLAN_YEARLY  = 'yearly'
    PLAN_CHOICES = [
        (PLAN_FREE,    'Free'),
        (PLAN_MONTHLY, 'Premium Monthly'),
        (PLAN_YEARLY,  'Premium Yearly'),
    ]

    user        = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                       related_name='subscription')
    plan        = models.CharField(max_length=10, choices=PLAN_CHOICES, default=PLAN_FREE)
    is_active   = models.BooleanField(default=True)
    started_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField(null=True, blank=True)
    razorpay_payment_id   = models.CharField(max_length=100, blank=True)
    razorpay_order_id     = models.CharField(max_length=100, blank=True)
    razorpay_subscription_id = models.CharField(max_length=100, blank=True)
    updated_at  = models.DateTimeField(auto_now=True)

    FREE_HABIT_LIMIT = 5

    @property
    def is_premium(self):
        if self.plan == self.PLAN_FREE:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    @property
    def habit_limit(self):
        return None if self.is_premium else self.FREE_HABIT_LIMIT

    @property
    def days_left(self):
        if not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)

    def to_dict(self):
        return {
            'plan':        self.plan,
            'is_premium':  self.is_premium,
            'habit_limit': self.habit_limit,
            'expires_at':  str(self.expires_at) if self.expires_at else None,
            'days_left':   self.days_left,
        }

    def __str__(self):
        return f"{self.user.email} — {self.plan}"


def get_or_create_subscription(user):
    sub, _ = Subscription.objects.get_or_create(user=user)
    return sub
