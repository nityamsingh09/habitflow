import json
from datetime import date, timedelta
from functools import wraps

from django.core.mail import send_mail
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Challenge, ChallengeParticipant, ChallengeLog, ChallengeInvite


def login_required_api(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required_api
def challenge_list(request):
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
    # Free users cannot create challenges
    try:
        from payments.models import get_or_create_subscription
        sub = get_or_create_subscription(request.user)
        if not sub.is_premium:
            return JsonResponse({'error': 'free_plan', 'message': 'Upgrade to Premium to create challenges.'}, status=403)
    except Exception:
        pass

    ch = Challenge.objects.create(
        creator=request.user,
        title=body.get('title', ''),
        description=body.get('description', ''),
        habit_name=body.get('habit_name', ''),
        habit_icon=body.get('habit_icon', '🎯'),
        duration_days=duration,
        start_date=today,
        end_date=end,
        is_public=body.get('is_public', True),
    )
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
    # Free users cannot join challenges
    try:
        from payments.models import get_or_create_subscription
        sub = get_or_create_subscription(request.user)
        if not sub.is_premium:
            return JsonResponse({'error': 'free_plan', 'message': 'Upgrade to Premium to join challenges.'}, status=403)
    except Exception:
        pass
    p, created = ChallengeParticipant.objects.get_or_create(challenge=ch, user=request.user)
    # Mark any pending invite as accepted
    ChallengeInvite.objects.filter(challenge=ch, invited_user=request.user, status='pending').update(
        status='accepted', responded_at=timezone.now()
    )
    return JsonResponse({'ok': True, 'already_in': not created})


@csrf_exempt
@login_required_api
@require_http_methods(['POST'])
def decline_challenge(request, challenge_id):
    try:
        ch = Challenge.objects.get(id=challenge_id)
    except Challenge.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    ChallengeInvite.objects.filter(challenge=ch, invited_user=request.user, status='pending').update(
        status='declined', responded_at=timezone.now()
    )
    return JsonResponse({'ok': True})


@csrf_exempt
@login_required_api
@require_http_methods(['POST'])
def log_challenge(request, challenge_id):
    try:
        ch = Challenge.objects.get(id=challenge_id)
        p  = ChallengeParticipant.objects.get(challenge=ch, user=request.user)
    except (Challenge.DoesNotExist, ChallengeParticipant.DoesNotExist):
        return JsonResponse({'error': 'Not found / not joined'}, status=404)
    today = date.today()
    if today < ch.start_date or today > ch.end_date:
        return JsonResponse({'error': 'Challenge not active today'}, status=400)
    log, created = ChallengeLog.objects.get_or_create(participant=p, log_date=today)
    if not created:
        log.delete()
        return JsonResponse({'ok': True, 'action': 'removed', 'logs': p.log_count})
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


# ── INVITE SYSTEM ──────────────────────────────────────────────────────────

@csrf_exempt
@login_required_api
@require_http_methods(['POST'])
def invite_to_challenge(request, challenge_id):
    """Invite a friend by username or email."""
    try:
        ch = Challenge.objects.get(id=challenge_id)
    except Challenge.DoesNotExist:
        return JsonResponse({'error': 'Challenge not found'}, status=404)

    # Must be participant to invite
    if not ChallengeParticipant.objects.filter(challenge=ch, user=request.user).exists():
        return JsonResponse({'error': 'Join the challenge first before inviting'}, status=403)

    body       = json.loads(request.body)
    identifier = body.get('identifier', '').strip()   # username or email
    if not identifier:
        return JsonResponse({'error': 'Provide a username or email'}, status=400)

    from accounts.models import User
    from social.models import UserProfile

    invited_user = None
    # Try by username
    try:
        profile = UserProfile.objects.get(username__iexact=identifier)
        invited_user = profile.user
    except UserProfile.DoesNotExist:
        pass
    # Try by email
    if not invited_user:
        try:
            invited_user = User.objects.get(email__iexact=identifier)
        except User.DoesNotExist:
            pass

    if not invited_user:
        return JsonResponse({'error': f'No user found for "{identifier}"'}, status=404)

    if invited_user == request.user:
        return JsonResponse({'error': "You can't invite yourself"}, status=400)

    # Already a participant?
    if ChallengeParticipant.objects.filter(challenge=ch, user=invited_user).exists():
        return JsonResponse({'error': f'{invited_user.display_name} is already in this challenge'}, status=400)

    # Already invited?
    existing = ChallengeInvite.objects.filter(challenge=ch, invited_user=invited_user).first()
    if existing and existing.status == 'pending':
        return JsonResponse({'error': f'{invited_user.display_name} already has a pending invite'}, status=400)

    invite = ChallengeInvite.objects.create(
        challenge=ch,
        invited_by=request.user,
        invited_user=invited_user,
        invited_email=invited_user.email,
    )

    # Send email notification
    try:
        send_mail(
            subject=f'⚔️ {request.user.display_name} invited you to a HabitFlow challenge!',
            message=(
                f"Hey {invited_user.display_name}!\n\n"
                f"{request.user.display_name} has invited you to join:\n\n"
                f"  ⚔️ {ch.habit_icon} {ch.title}\n"
                f"  📅 {ch.duration_days}-day challenge\n"
                f"  📝 {ch.habit_name}\n\n"
                f"Open HabitFlow to accept or decline:\n"
                f"https://habitflow.vercel.app\n\n"
                f"— The HabitFlow Team"
            ),
            from_email=None,
            recipient_list=[invited_user.email],
            fail_silently=True,
        )
    except Exception:
        pass

    return JsonResponse({'ok': True, 'invited': invited_user.display_name, 'invite_id': invite.id})


@login_required_api
def my_invites(request):
    """Pending invites for the current user."""
    invites = ChallengeInvite.objects.filter(
        invited_user=request.user, status='pending'
    ).select_related('challenge', 'invited_by').order_by('-created_at')
    return JsonResponse([i.to_dict() for i in invites], safe=False)


@login_required_api
def challenge_invites(request, challenge_id):
    """List of invites sent for a specific challenge (for the creator/participants)."""
    try:
        ch = Challenge.objects.get(id=challenge_id)
    except Challenge.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    invites = ch.invites.select_related('invited_user', 'invited_by').all()
    return JsonResponse([{
        'id':       i.id,
        'user':     i.invited_user.display_name if i.invited_user else i.invited_email,
        'status':   i.status,
        'sent_at':  str(i.created_at),
    } for i in invites], safe=False)
