import json
from datetime import date, timedelta, datetime
from functools import wraps

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Habit, HabitLog, Badge, BADGE_DEFINITIONS


def _emit_activity(user, habit, event_type, meta=None):
    """Fire-and-forget: create an ActivityEvent if the habit is public."""
    try:
        if not habit.is_public:
            return
        from social.models import ActivityEvent
        ActivityEvent.objects.create(user=user, habit=habit, event_type=event_type, meta=meta or {})
    except Exception:
        pass

def _award_xp_for_log(user, habit, streak, new_badges):
    """Award XP when a habit is logged."""
    try:
        from gamification.models import UserXP, XP_PER_LOG, XP_STREAK_BONUS, XP_BADGE_BONUS
        from gamification.views import check_and_complete_quests
        xp = UserXP.objects.get_or_create(user=user)[0]
        xp.add_xp(XP_PER_LOG, f'Logged: {habit.name}')
        bonus = XP_STREAK_BONUS.get(streak, 0)
        if bonus:
            xp.add_xp(bonus, f'Streak milestone: {streak} days on {habit.name}')
        for _ in new_badges:
            xp.add_xp(XP_BADGE_BONUS, f'Badge earned on {habit.name}')
        check_and_complete_quests(user)
    except Exception:
        pass



def login_required_api(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required.', 'redirect': '/auth/login/'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def login_required_page(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/auth/login/')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required_page
def index(request):
    return render(request, 'habits/index.html', {
        'user': request.user,
        'show_verified_toast': request.GET.get('verified') == '1',
    })


def evaluate_badges(habit, logged_dates):
    newly_earned = []
    today = date.today()
    total = len(logged_dates)

    streak = 0
    check = today
    while check in logged_dates:
        streak += 1
        check -= timedelta(days=1)

    for badge_id, _, emoji, _, ctype, threshold in BADGE_DEFINITIONS:
        if ctype != 'streak':
            continue
        if streak >= threshold:
            b, created = Badge.objects.get_or_create(badge_id=badge_id, habit=habit,
                                                      defaults={'earned_at': today})
            if created:
                newly_earned.append(b.to_dict())
                _emit_activity(habit.user, habit, 'streak', {'streak': streak, 'badge_id': badge_id})

    for badge_id, _, emoji, _, ctype, threshold in BADGE_DEFINITIONS:
        if ctype != 'total':
            continue
        if total >= threshold:
            b, created = Badge.objects.get_or_create(badge_id=badge_id, habit=habit,
                                                      defaults={'earned_at': today})
            if created:
                newly_earned.append(b.to_dict())
                _emit_activity(habit.user, habit, 'badge', {'badge_id': badge_id, 'total': total})

    if habit.target_days and habit.target_start:
        target_end = habit.target_start + timedelta(days=habit.target_days - 1)
        window_logs = {d for d in logged_dates if habit.target_start <= d <= target_end}

        if len(window_logs) >= habit.target_days:
            b, created = Badge.objects.get_or_create(
                badge_id='target_complete', habit=habit,
                defaults={'earned_at': today, 'extra_data': {'target_days': habit.target_days}}
            )
            if created:
                newly_earned.append(b.to_dict())
                _emit_activity(habit.user, habit, 'target', {'target_days': habit.target_days})

            sorted_logs = sorted(window_logs)
            if len(sorted_logs) >= habit.target_days:
                days_saved = (target_end - sorted_logs[habit.target_days - 1]).days
                if days_saved >= 10:
                    b, created = Badge.objects.get_or_create(
                        badge_id='target_early', habit=habit,
                        defaults={'earned_at': today, 'extra_data': {'days_saved': days_saved}}
                    )
                    if created:
                        newly_earned.append(b.to_dict())

            total_window_days = (min(target_end, today) - habit.target_start).days + 1
            if len(window_logs) >= total_window_days:
                b, created = Badge.objects.get_or_create(
                    badge_id='target_perfect', habit=habit,
                    defaults={'earned_at': today}
                )
                if created:
                    newly_earned.append(b.to_dict())

    target_complete_count = Badge.objects.filter(badge_id='target_complete', habit__user=habit.user).count()
    if target_complete_count >= 3:
        b, created = Badge.objects.get_or_create(
            badge_id='multi_target', habit=habit,
            defaults={'earned_at': today, 'extra_data': {'targets_completed': target_complete_count}}
        )
        if created:
            newly_earned.append(b.to_dict())

    return newly_earned


@csrf_exempt
@login_required_api
@require_http_methods(["GET", "POST"])
def habits(request):
    if request.method == "GET":
        return JsonResponse([h.to_dict() for h in Habit.objects.filter(user=request.user)], safe=False)

    body = json.loads(request.body)

    # ── Subscription limit check ──────────────────────────────────────────
    try:
        from payments.models import get_or_create_subscription
        sub = get_or_create_subscription(request.user)
        if not sub.is_premium:
            current_count = Habit.objects.filter(user=request.user).count()
            if current_count >= sub.FREE_HABIT_LIMIT:
                return JsonResponse({
                    'error':      'free_limit',
                    'message':    f'Free plan allows up to {sub.FREE_HABIT_LIMIT} habits. Upgrade to Premium for unlimited habits.',
                    'limit':      sub.FREE_HABIT_LIMIT,
                    'current':    current_count,
                }, status=403)
    except Exception:
        pass  # payments app not set up — allow creation

    new_id = f"custom_{str(request.user.id).replace('-','')[:8]}_{datetime.now().timestamp()}".replace('.','_')
    target_days, target_start = None, None
    if body.get('target_days'):
        try:
            target_days = int(body['target_days'])
            target_start = date.today()
        except (ValueError, TypeError):
            pass

    habit = Habit.objects.create(
        habit_id=new_id, user=request.user,
        name=body.get('name',''), icon=body.get('icon','⭐'),
        category=body.get('category','General'), color=body.get('color','#c8ff00'),
        is_default=False, is_public=body.get('is_public', True),
        target_days=target_days, target_start=target_start,
    )
    return JsonResponse(habit.to_dict(), status=201)


@csrf_exempt
@login_required_api
@require_http_methods(["PUT", "DELETE"])
def habit_detail(request, habit_id):
    try:
        habit = Habit.objects.get(habit_id=habit_id, user=request.user)
    except Habit.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    if request.method == "PUT":
        updates = json.loads(request.body)
        for field in ("name", "icon", "category", "color"):
            if field in updates:
                setattr(habit, field, updates[field])
        if 'is_public' in updates:
            habit.is_public = bool(updates['is_public'])
        if 'target_days' in updates:
            td = updates['target_days']
            if td:
                try:
                    habit.target_days = int(td)
                    if not habit.target_start:
                        habit.target_start = date.today()
                except (ValueError, TypeError):
                    habit.target_days = None; habit.target_start = None
            else:
                habit.target_days = None; habit.target_start = None
        habit.save()
        return JsonResponse(habit.to_dict())

    habit.delete()
    return JsonResponse({"success": True})


@csrf_exempt
@login_required_api
@require_http_methods(["POST"])
def log_habit(request):
    payload  = json.loads(request.body)
    habit_id = payload["habit_id"]
    log_date = date.fromisoformat(payload.get("date", str(date.today())))

    try:
        habit = Habit.objects.get(habit_id=habit_id, user=request.user)
    except Habit.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)

    log_entry, created = HabitLog.objects.get_or_create(habit=habit, log_date=log_date)
    if not created:
        log_entry.delete()
        return JsonResponse({"status": "removed", "date": str(log_date), "habit_id": habit_id, "new_badges": []})

    # Emit activity for public habits
    _emit_activity(request.user, habit, 'log', {
        'habit_name': habit.name, 'habit_icon': habit.icon, 'habit_color': habit.color
    })

    logged_dates = set(HabitLog.objects.filter(habit=habit).values_list('log_date', flat=True))
    new_badges   = evaluate_badges(habit, logged_dates)

    # Compute streak for XP bonus
    streak = 0
    check  = log_date
    while check in logged_dates:
        streak += 1; check -= timedelta(days=1)
    _award_xp_for_log(request.user, habit, streak, new_badges)
    return JsonResponse({"status": "added", "date": str(log_date), "habit_id": habit_id, "new_badges": new_badges})


@login_required_api
@require_http_methods(["GET"])
def get_logs(request):
    logs = {}
    for entry in HabitLog.objects.select_related('habit').filter(habit__user=request.user):
        ds = str(entry.log_date)
        logs.setdefault(ds, []).append(entry.habit.habit_id)
    return JsonResponse(logs)


@login_required_api
@require_http_methods(["GET"])
def get_stats(request):
    today      = date.today()
    all_habits = Habit.objects.filter(user=request.user)
    logs_by_habit = {}
    for entry in HabitLog.objects.select_related('habit').filter(habit__user=request.user):
        logs_by_habit.setdefault(entry.habit.habit_id, set()).add(entry.log_date)

    stats = {}
    for habit in all_habits:
        hid          = habit.habit_id
        logged_dates = logs_by_habit.get(hid, set())
        total        = len(logged_dates)
        streak = 0
        check  = today
        while check in logged_dates:
            streak += 1; check -= timedelta(days=1)

        heatmap = {str(today - timedelta(days=i)): 1 if (today - timedelta(days=i)) in logged_dates else 0
                   for i in range(365)}

        target_progress = None
        if habit.target_days and habit.target_start:
            target_end  = habit.target_start + timedelta(days=habit.target_days - 1)
            window_logs = {d for d in logged_dates if habit.target_start <= d <= target_end}
            target_progress = {
                "target_days":    habit.target_days,
                "target_start":   str(habit.target_start),
                "target_end":     str(target_end),
                "completed":      len(window_logs),
                "days_remaining": max(0, (target_end - today).days),
                "is_complete":    len(window_logs) >= habit.target_days,
                "is_expired":     today > target_end and len(window_logs) < habit.target_days,
            }
        stats[hid] = {"streak": streak, "total": total, "heatmap": heatmap, "target_progress": target_progress}
    return JsonResponse(stats)


@login_required_api
@require_http_methods(["GET"])
def get_today(request):
    completed = list(HabitLog.objects.filter(
        log_date=date.today(), habit__user=request.user
    ).values_list('habit__habit_id', flat=True))
    return JsonResponse(completed, safe=False)


@login_required_api
@require_http_methods(["GET"])
def get_badges(request):
    badges = Badge.objects.select_related('habit').filter(habit__user=request.user).order_by('-earned_at')
    return JsonResponse([b.to_dict() for b in badges], safe=False)


@require_http_methods(["GET"])
def get_badge_definitions(request):
    return JsonResponse([
        {"badge_id": b[0], "name": b[1], "emoji": b[2], "description": b[3]}
        for b in BADGE_DEFINITIONS
    ], safe=False)


@login_required_api
@require_http_methods(["GET"])
def get_me(request):
    u = request.user
    sub_data = {'plan':'free','is_premium':False,'habit_limit':5}
    try:
        from payments.models import get_or_create_subscription
        sub_data = get_or_create_subscription(u).to_dict()
    except Exception:
        pass
    return JsonResponse({
        "email":        u.email,
        "display_name": u.display_name,
        "avatar_url":   u.avatar_url,
        "subscription": sub_data,
    })
