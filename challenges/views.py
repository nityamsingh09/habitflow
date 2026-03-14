import json
from datetime import date, timedelta
from functools import wraps

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Challenge, ChallengeParticipant, ChallengeLog


def login_required_api(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required_api
def challenge_list(request):
    """Active public challenges + challenges I'm in."""
    public = Challenge.objects.filter(is_public=True).order_by('-created_at')[:20]
    mine   = Challenge.objects.filter(participants__user=request.user).order_by('-created_at')[:10]
    all_ch = list({c.id: c for c in list(public) + list(mine)}.values())
    return JsonResponse([c.to_dict(user=request.user) for c in all_ch], safe=False)


@csrf_exempt
@login_required_api
@require_http_methods(['POST'])
def create_challenge(request):
    body = json.loads(request.body)
    today = date.today()
    duration = int(body.get('duration_days', 7))
    end = today + timedelta(days=duration - 1)
    ch = Challenge.objects.create(
        creator=request.user,
        title=body.get('title',''),
        description=body.get('description',''),
        habit_name=body.get('habit_name',''),
        habit_icon=body.get('habit_icon','🎯'),
        duration_days=duration,
        start_date=today,
        end_date=end,
        is_public=body.get('is_public', True),
    )
    # Creator auto-joins
    ChallengeParticipant.objects.create(challenge=ch, user=request.user)
    return JsonResponse({'ok': True, 'challenge': ch.to_dict(user=request.user)}, status=201)


@csrf_exempt
@login_required_api
@require_http_methods(['POST'])
def join_challenge(request, challenge_id):
    try:
        ch = Challenge.objects.get(id=challenge_id)
    except Challenge.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    if date.today() > ch.end_date:
        return JsonResponse({'error': 'Challenge has ended'}, status=400)
    p, created = ChallengeParticipant.objects.get_or_create(challenge=ch, user=request.user)
    return JsonResponse({'ok': True, 'already_in': not created})


@csrf_exempt
@login_required_api
@require_http_methods(['POST'])
def log_challenge(request, challenge_id):
    try:
        ch = Challenge.objects.get(id=challenge_id)
        p  = ChallengeParticipant.objects.get(challenge=ch, user=request.user)
    except (Challenge.DoesNotExist, ChallengeParticipant.DoesNotExist):
        return JsonResponse({'error': 'Not found'}, status=404)

    today = date.today()
    if today < ch.start_date or today > ch.end_date:
        return JsonResponse({'error': 'Challenge not active today'}, status=400)

    log, created = ChallengeLog.objects.get_or_create(participant=p, log_date=today)
    if not created:
        log.delete()
        return JsonResponse({'ok': True, 'action': 'removed', 'logs': p.log_count})

    # Check completion
    if p.log_count >= ch.duration_days:
        p.completed = True
        p.save(update_fields=['completed'])
        try:
            from gamification.models import UserXP
            xp, _ = UserXP.objects.get_or_create(user=request.user)
            xp.add_xp(500, f'Won challenge: {ch.title}')
        except Exception:
            pass

    return JsonResponse({'ok': True, 'action': 'added', 'logs': p.log_count, 'completed': p.completed})


@login_required_api
def challenge_detail(request, challenge_id):
    try:
        ch = Challenge.objects.get(id=challenge_id)
    except Challenge.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    return JsonResponse(ch.to_dict(user=request.user))
