"""
Management command: python manage.py send_weekly_recap
Run weekly via cron: 0 8 * * 1 (every Monday 8am)
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from datetime import date, timedelta
from accounts.models import User
from habits.models import Habit, HabitLog, Badge


class Command(BaseCommand):
    help = 'Send weekly habit recap emails to all verified users'

    def handle(self, *args, **options):
        today     = date.today()
        week_ago  = today - timedelta(days=7)
        sent = 0

        for user in User.objects.filter(is_verified=True, is_active=True):
            try:
                habits     = Habit.objects.filter(user=user)
                logs_week  = HabitLog.objects.filter(habit__user=user,
                                                      log_date__gte=week_ago,
                                                      log_date__lte=today)
                total_week = logs_week.count()
                total_all  = HabitLog.objects.filter(habit__user=user).count()
                badges_new = Badge.objects.filter(habit__user=user,
                                                   earned_at__gte=week_ago).count()

                # Best streak
                best_streak, best_name = 0, ''
                for h in habits:
                    h_logs = set(HabitLog.objects.filter(habit=h).values_list('log_date', flat=True))
                    s, c   = 0, today
                    while c in h_logs: s += 1; c -= timedelta(days=1)
                    if s > best_streak: best_streak, best_name = s, f"{h.icon} {h.name}"

                if total_week == 0 and total_all == 0:
                    continue  # Skip users with no activity ever

                subject = f"🔥 Your HabitFlows week — {total_week} habits completed"
                body = f"""Hey {user.display_name}!

Here's your HabitFlows weekly recap:

📊 This Week
  • Habits completed: {total_week}
  • Total all-time: {total_all}
  {f'• New badges: 🏅 {badges_new}' if badges_new else ''}

{f'🔥 Best streak: {best_streak} days on {best_name}' if best_streak else ''}

{'Great week! Keep the momentum going 💪' if total_week >= 5 else 'Every habit counts — even one a day makes a difference 🌱'}

Open HabitFlows → https://habitflows.vercel.app

— The HabitFlows Team
"""
                send_mail(subject, body, None, [user.email], fail_silently=True)
                sent += 1
            except Exception as e:
                self.stdout.write(f"Error for {user.email}: {e}")

        self.stdout.write(self.style.SUCCESS(f"✓ Sent weekly recap to {sent} users"))
