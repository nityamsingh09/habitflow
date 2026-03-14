import json
import random
from datetime import date, timedelta
from functools import wraps

from django.db.models import Avg, Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from habits.models import Habit, HabitLog, Badge
from .models import (UserXP, XPTransaction, DailyQuest, StreakFreeze,
                     MoodLog, QUEST_TYPES, XP_PER_LOG, XP_BADGE_BONUS, XP_DAILY_QUEST)


def login_required_api(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def _ensure_xp(user):
    xp, _ = UserXP.objects.get_or_create(user=user)
    return xp


# ── XP & Level ────────────────────────────────────────────────────────────

@login_required_api
def my_xp(request):
    xp = _ensure_xp(request.user)
    recent = list(XPTransaction.objects.filter(user=request.user)[:10].values('amount','reason','created_at'))
    for r in recent:
        r['created_at'] = str(r['created_at'])
    return JsonResponse({
        'level':    xp.level_info(),
        'freezes':  xp.streak_freezes,
        'recent':   recent,
    })


# ── Daily Quests ──────────────────────────────────────────────────────────

def _generate_quests(user, today):
    """Create today's quests if they don't exist."""
    habit_count = Habit.objects.filter(user=user).count()
    # Pick 3 quests for today deterministically
    random.seed(str(user.id) + str(today))
    pool = list(QUEST_TYPES)
    if habit_count < 5:
        pool = [q for q in pool if q[0] != 'log_5' and q[0] != 'log_all']
    chosen = random.sample(pool, min(3, len(pool)))
    for q in chosen:
        DailyQuest.objects.get_or_create(
            user=user, quest_type=q[0], quest_date=today,
            defaults={'xp_reward': q[2]}
        )


@login_required_api
def daily_quests(request):
    today = date.today()
    _generate_quests(request.user, today)
    quests = DailyQuest.objects.filter(user=request.user, quest_date=today)
    return JsonResponse([q.to_dict() for q in quests], safe=False)


def check_and_complete_quests(user):
    """Called after each habit log — check if any quests are now complete."""
    today = date.today()
    _generate_quests(user, today)
    quests = DailyQuest.objects.filter(user=user, quest_date=today, completed=False)
    logs_today = HabitLog.objects.filter(habit__user=user, log_date=today).count()
    total_habits = Habit.objects.filter(user=user).count()
    xp_obj = _ensure_xp(user)
    newly_completed = []

    for q in quests:
        done = False
        if q.quest_type == 'log_3'   and logs_today >= 3:   done = True
        if q.quest_type == 'log_5'   and logs_today >= 5:   done = True
        if q.quest_type == 'log_all' and total_habits > 0 and logs_today >= total_habits: done = True
        if q.quest_type == 'streak_any':
            for h in Habit.objects.filter(user=user):
                h_logs = set(HabitLog.objects.filter(habit=h).values_list('log_date', flat=True))
                if today in h_logs:
                    s, c = 0, today
                    while c in h_logs: s += 1; c -= timedelta(days=1)
                    if s >= 2: done = True; break
        if done:
            q.completed = True
            q.completed_at = timezone.now()
            q.save()
            xp_obj.add_xp(q.xp_reward, f'Daily quest: {q.quest_type}')
            newly_completed.append(q.to_dict())

    return newly_completed


# ── Streak Freeze ─────────────────────────────────────────────────────────

@csrf_exempt
@login_required_api
@require_http_methods(['POST'])
def use_streak_freeze(request):
    body     = json.loads(request.body)
    habit_id = body.get('habit_id')
    freeze_date = date.fromisoformat(body.get('date', str(date.today() - timedelta(days=1))))

    try:
        habit = Habit.objects.get(habit_id=habit_id, user=request.user)
    except Habit.DoesNotExist:
        return JsonResponse({'error': 'Habit not found'}, status=404)

    xp = _ensure_xp(request.user)
    if xp.streak_freezes < 1:
        return JsonResponse({'error': 'No streak freezes available. Earn more XP to unlock them.'}, status=400)

    _, created = StreakFreeze.objects.get_or_create(
        habit=habit, freeze_date=freeze_date,
        defaults={'user': request.user}
    )
    if not created:
        return JsonResponse({'error': 'Already frozen that date'}, status=400)

    # Also create a HabitLog for that date so streak doesn't break
    HabitLog.objects.get_or_create(habit=habit, log_date=freeze_date)
    xp.streak_freezes -= 1
    xp.save(update_fields=['streak_freezes', 'updated_at'])

    return JsonResponse({'ok': True, 'freezes_remaining': xp.streak_freezes})


@csrf_exempt
@login_required_api
@require_http_methods(['POST'])
def buy_streak_freeze(request):
    """Spend 300 XP to get 1 streak freeze."""
    xp = _ensure_xp(request.user)
    if xp.total_xp < 300:
        return JsonResponse({'error': f'Need 300 XP (you have {xp.total_xp})'}, status=400)
    xp.total_xp -= 300
    xp.streak_freezes += 1
    xp.save(update_fields=['total_xp', 'streak_freezes', 'updated_at'])
    XPTransaction.objects.create(user=request.user, amount=-300, reason='Bought streak freeze')
    return JsonResponse({'ok': True, 'freezes': xp.streak_freezes, 'total_xp': xp.total_xp})


# ── Mood Tracking ─────────────────────────────────────────────────────────

@csrf_exempt
@login_required_api
def mood(request):
    if request.method == 'GET':
        days = int(request.GET.get('days', 30))
        start = date.today() - timedelta(days=days)
        logs  = MoodLog.objects.filter(user=request.user, log_date__gte=start).order_by('log_date')
        return JsonResponse([m.to_dict() for m in logs], safe=False)

    body = json.loads(request.body)
    mood_val = int(body.get('mood', 3))
    mood_val = max(1, min(5, mood_val))
    log_date = date.fromisoformat(body.get('date', str(date.today())))
    note = body.get('note', '')[:200]

    m, _ = MoodLog.objects.update_or_create(
        user=request.user, log_date=log_date,
        defaults={'mood': mood_val, 'note': note}
    )
    return JsonResponse({'ok': True, 'mood': m.to_dict()})


# ── AI / Rule-based Insights ──────────────────────────────────────────────

@login_required_api
def weekly_insights(request):
    user  = request.user
    today = date.today()
    week_ago   = today - timedelta(days=7)
    month_ago  = today - timedelta(days=30)

    habits = list(Habit.objects.filter(user=user))
    all_logs = list(HabitLog.objects.filter(habit__user=user))

    # Build per-habit stats
    logs_by_habit = {}
    for log in all_logs:
        logs_by_habit.setdefault(log.habit_id, set()).add(log.log_date)

    # Week over week
    this_week  = sum(1 for l in all_logs if week_ago <= l.log_date <= today)
    last_week  = sum(1 for l in all_logs if (week_ago - timedelta(7)) <= l.log_date < week_ago)
    wow_pct    = round((this_week - last_week) / max(last_week, 1) * 100)

    # Best day of week
    day_counts = [0]*7
    for log in all_logs:
        if log.log_date >= month_ago:
            day_counts[log.log_date.weekday()] += 1
    day_names  = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    best_day   = day_names[day_counts.index(max(day_counts))] if any(day_counts) else None
    worst_day  = day_names[day_counts.index(min(day_counts))] if any(day_counts) else None

    # Best habit
    best_habit = None
    best_streak = 0
    for habit in habits:
        h_logs = logs_by_habit.get(habit.habit_id, set())
        s, c   = 0, today
        while c in h_logs: s += 1; c -= timedelta(days=1)
        if s > best_streak:
            best_streak = s
            best_habit  = habit

    # Habit correlations: habits often done together
    correlations = []
    date_habit_map = {}  # date -> set of habit_ids
    for log in all_logs:
        date_habit_map.setdefault(log.log_date, set()).add(log.habit_id)

    if len(habits) >= 2:
        for i, h1 in enumerate(habits[:5]):
            for h2 in habits[i+1:6]:
                both  = sum(1 for d, ids in date_habit_map.items() if h1.habit_id in ids and h2.habit_id in ids)
                total = sum(1 for d, ids in date_habit_map.items() if h1.habit_id in ids)
                if total > 5 and both / total > 0.5:
                    correlations.append({
                        'habit1': h1.name, 'icon1': h1.icon,
                        'habit2': h2.name, 'icon2': h2.icon,
                        'pct': round(both/total*100),
                    })
    correlations.sort(key=lambda x: x['pct'], reverse=True)

    # Mood vs habits correlation
    mood_logs = {m.log_date: m.mood for m in MoodLog.objects.filter(user=user, log_date__gte=month_ago)}
    high_mood_days  = {d for d, m in mood_logs.items() if m >= 4}
    low_mood_days   = {d for d, m in mood_logs.items() if m <= 2}
    mood_boosters   = []
    for habit in habits:
        h_logs = logs_by_habit.get(habit.habit_id, set())
        if len(high_mood_days) > 2:
            hit = len(h_logs & high_mood_days) / len(high_mood_days)
            if hit > 0.6:
                mood_boosters.append({'name': habit.name, 'icon': habit.icon, 'pct': round(hit*100)})

    # Build insight sentences
    insights = []
    if wow_pct > 0:
        insights.append(f"📈 You completed {this_week} habits this week — {wow_pct}% more than last week. Keep it up!")
    elif wow_pct < -10:
        insights.append(f"📉 {this_week} completions this week vs {last_week} last week. You've got this — just start small.")
    else:
        insights.append(f"📊 Solid week! {this_week} habit completions, roughly the same as last week.")

    if best_day:
        insights.append(f"🗓️ Your strongest day this month is {best_day} — try to schedule key habits then.")
    if worst_day:
        insights.append(f"⚠️ {worst_day} is your weakest day. One small habit there could change everything.")
    if best_habit and best_streak >= 3:
        insights.append(f"🔥 {best_habit.icon} {best_habit.name} is on a {best_streak}-day streak — don't break it!")
    if correlations:
        c = correlations[0]
        insights.append(f"🔗 When you do {c['icon1']} {c['habit1']}, you also do {c['icon2']} {c['habit2']} {c['pct']}% of the time. They're a great pair!")
    if mood_boosters:
        b = mood_boosters[0]
        insights.append(f"😊 {b['icon']} {b['name']} appears on {b['pct']}% of your high-mood days. It seems to make you happier.")
    if not insights:
        insights.append("🌱 Start logging habits regularly to unlock personalized insights!")

    return JsonResponse({
        'insights':     insights,
        'this_week':    this_week,
        'last_week':    last_week,
        'wow_pct':      wow_pct,
        'best_day':     best_day,
        'worst_day':    worst_day,
        'best_streak':  best_streak,
        'best_habit':   {'name': best_habit.name, 'icon': best_habit.icon} if best_habit else None,
        'correlations': correlations[:3],
        'mood_boosters':mood_boosters[:3],
        'day_counts':   {day_names[i]: day_counts[i] for i in range(7)},
    })


# ── Habit Templates ───────────────────────────────────────────────────────

HABIT_TEMPLATES = [
    # Health
    {'name':'Morning Run','icon':'🏃','category':'Health','color':'#f97316','description':'Run or jog for at least 20 minutes'},
    {'name':'Drink 8 Glasses of Water','icon':'💧','category':'Health','color':'#60a5fa','description':'Stay hydrated every day'},
    {'name':'No Sugar','icon':'🚫','category':'Health','color':'#f87171','description':'Cut out added sugars for the day'},
    {'name':'Sleep 8 Hours','icon':'😴','category':'Health','color':'#a78bfa','description':'Get a full night\'s sleep'},
    {'name':'10-Minute Stretch','icon':'🧘','category':'Health','color':'#34d399','description':'Morning or evening stretch routine'},
    {'name':'Vitamins','icon':'💊','category':'Health','color':'#fbbf24','description':'Take your daily vitamins'},
    {'name':'Cold Shower','icon':'🚿','category':'Health','color':'#38bdf8','description':'Boost energy with a cold shower'},
    {'name':'No Alcohol','icon':'🍷','category':'Health','color':'#fb7185','description':'Alcohol-free day'},
    # Fitness
    {'name':'Gym Workout','icon':'💪','category':'Fitness','color':'#f97316','description':'Hit the gym for strength training'},
    {'name':'100 Push-Ups','icon':'🏋','category':'Fitness','color':'#c8ff00','description':'Do 100 push-ups throughout the day'},
    {'name':'10,000 Steps','icon':'👟','category':'Fitness','color':'#34d399','description':'Hit your daily step goal'},
    {'name':'Yoga','icon':'🧘','category':'Fitness','color':'#a78bfa','description':'30-minute yoga session'},
    {'name':'Cycling','icon':'🚴','category':'Fitness','color':'#fbbf24','description':'Cycle for at least 30 minutes'},
    # Mind
    {'name':'Meditate','icon':'🧠','category':'Mind','color':'#a78bfa','description':'10 minutes of mindfulness meditation'},
    {'name':'Journaling','icon':'📓','category':'Mind','color':'#fbbf24','description':'Write at least 3 sentences in a journal'},
    {'name':'Gratitude List','icon':'🙏','category':'Mind','color':'#34d399','description':'Write 3 things you\'re grateful for'},
    {'name':'Digital Detox Hour','icon':'📵','category':'Mind','color':'#60a5fa','description':'1 hour screen-free before bed'},
    {'name':'Deep Breathing','icon':'🌬','category':'Mind','color':'#38bdf8','description':'5 minutes of box breathing'},
    # Learning
    {'name':'Read 30 Minutes','icon':'📚','category':'Learning','color':'#c8ff00','description':'Read any book for 30 minutes'},
    {'name':'Learn a Language','icon':'🌍','category':'Learning','color':'#60a5fa','description':'15 minutes on Duolingo or similar'},
    {'name':'Online Course','icon':'🎓','category':'Learning','color':'#a78bfa','description':'1 lesson from an online course'},
    {'name':'No Social Media','icon':'📱','category':'Learning','color':'#f87171','description':'Reclaim focus time'},
    {'name':'Write 500 Words','icon':'✍️','category':'Learning','color':'#fbbf24','description':'Blog, fiction, or journal writing'},
    {'name':'Practice Coding','icon':'💻','category':'Learning','color':'#34d399','description':'1 hour of coding practice'},
    # Finance
    {'name':'Track Expenses','icon':'💰','category':'Finance','color':'#34d399','description':'Log every expense today'},
    {'name':'No Impulse Buys','icon':'🛑','category':'Finance','color':'#f87171','description':'Only buy what\'s on your list'},
    {'name':'Save ₹100','icon':'🏦','category':'Finance','color':'#fbbf24','description':'Transfer at least ₹100 to savings'},
    {'name':'Review Budget','icon':'📊','category':'Finance','color':'#60a5fa','description':'Check your monthly spending'},
    # Social
    {'name':'Call a Friend','icon':'📞','category':'Social','color':'#f97316','description':'Reach out to someone you care about'},
    {'name':'Random Act of Kindness','icon':'💝','category':'Social','color':'#fb7185','description':'Do something nice for someone'},
    {'name':'Family Time','icon':'👨‍👩‍👧','category':'Social','color':'#fbbf24','description':'Spend quality time with family'},
]

@require_http_methods(['GET'])
def habit_templates(request):
    category = request.GET.get('category')
    templates = HABIT_TEMPLATES
    if category:
        templates = [t for t in templates if t['category'] == category]
    categories = sorted(set(t['category'] for t in HABIT_TEMPLATES))
    return JsonResponse({'templates': templates, 'categories': categories})
