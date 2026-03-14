import json
from datetime import date, timedelta
from functools import wraps

from django.db import models as dm
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from accounts.models import User
from habits.models import Habit, HabitLog, Badge
from .models import (UserProfile, Follow, FriendRequest, ActivityEvent,
                     Reaction, Comment, REACTIONS, are_friends, get_friends, is_following,
                     GlobalMessage, DirectMessage)


def login_required_api(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required', 'redirect': '/auth/login/'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper

def login_required_page(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/auth/login/')
        return view_func(request, *args, **kwargs)
    return wrapper


def _ensure_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def _user_stats(user):
    today = date.today()
    all_logs = set(HabitLog.objects.filter(habit__user=user).values_list('log_date', flat=True))
    best_streak = 0
    for habit in Habit.objects.filter(user=user):
        h_logs = set(HabitLog.objects.filter(habit=habit).values_list('log_date', flat=True))
        s, check = 0, today
        while check in h_logs:
            s += 1; check -= timedelta(days=1)
        best_streak = max(best_streak, s)
    weekly = HabitLog.objects.filter(
        habit__user=user, log_date__gte=today-timedelta(days=6), log_date__lte=today
    ).count()
    return {
        'total_completions': len(all_logs),
        'best_streak':       best_streak,
        'badge_count':       Badge.objects.filter(habit__user=user).count(),
        'weekly':            weekly,
    }


def _friend_status(viewer, user):
    if viewer == user:
        return 'self'
    try:
        fr = FriendRequest.objects.get(
            Q(from_user=viewer, to_user=user) | Q(from_user=user, to_user=viewer)
        )
        if fr.status == 'accepted': return 'friends'
        if fr.status == 'pending' and fr.from_user == viewer: return 'sent'
        if fr.status == 'pending' and fr.to_user == viewer: return 'received'
    except FriendRequest.DoesNotExist:
        pass
    return 'none'


def _public_profile_dict(user, viewer=None):
    profile = _ensure_profile(user)
    stats   = _user_stats(user)
    fstatus = _friend_status(viewer, user) if viewer else 'none'
    following_them = is_following(viewer, user) if viewer and viewer != user else False
    follower_count = Follow.objects.filter(following=user).count()
    following_count = Follow.objects.filter(follower=user).count()
    return {
        'id':              str(user.id),
        'username':        profile.username,
        'display_name':    user.display_name,
        'avatar_url':      user.avatar_url,
        'bio':             profile.bio,
        'is_public':       profile.is_public,
        'date_joined':     str(user.date_joined.date()),
        'friend_status':   fstatus,
        'following_them':  following_them,
        'follower_count':  follower_count,
        'following_count': following_count,
        **stats,
    }


def _event_dict(event, viewer):
    """Serialise an ActivityEvent with reaction counts and whether viewer reacted."""
    reaction_counts = {}
    for r in REACTIONS:
        cnt = event.reactions.filter(emoji=r).count()
        if cnt: reaction_counts[r] = cnt
    my_reactions = list(event.reactions.filter(user=viewer).values_list('emoji', flat=True))
    comments = [c.to_dict() for c in event.comments.all()]
    habit    = event.habit

    profile_username = ''
    try:
        profile_username = event.user.profile.username
    except Exception:
        pass

    return {
        'id':            event.id,
        'user_id':       str(event.user.id),
        'display_name':  event.user.display_name,
        'avatar_url':    event.user.avatar_url,
        'username':      profile_username,
        'event_type':    event.event_type,
        'meta':          event.meta,
        'habit_name':    habit.name if habit else '',
        'habit_icon':    habit.icon if habit else '',
        'habit_color':   habit.color if habit else '#c8ff00',
        'created_at':    event.created_at.strftime('%b %d · %H:%M'),
        'reactions':     reaction_counts,
        'my_reactions':  my_reactions,
        'comments':      comments,
        'comment_count': len(comments),
    }


# ── Pages ──────────────────────────────────────────────────────────────────

@login_required_page
def social_page(request):
    _ensure_profile(request.user)
    return render(request, 'social/social.html', {'user': request.user})


# ── Leaderboard ─────────────────────────────────────────────────────────────

@login_required_api
def leaderboard(request):
    category = request.GET.get('by', 'streak')
    limit    = min(int(request.GET.get('limit', 50)), 100)
    public_users = User.objects.filter(profile__is_public=True, is_verified=True).select_related('profile')

    rows = []
    for user in public_users:
        s = _user_stats(user)
        rows.append({
            'id':            str(user.id),
            'username':      user.profile.username,
            'display_name':  user.display_name,
            'avatar_url':    user.avatar_url,
            'is_me':         user == request.user,
            'is_friend':     are_friends(request.user, user),
            'is_following':  is_following(request.user, user),
            **s,
        })

    sort_key = {
        'streak': lambda r: r['best_streak'],
        'total':  lambda r: r['total_completions'],
        'badges': lambda r: r['badge_count'],
    }.get(category, lambda r: r['best_streak'])

    rows.sort(key=sort_key, reverse=True)
    viewer_rank = next((i+1 for i, r in enumerate(rows) if r['is_me']), None)
    rows = rows[:limit]
    for i, r in enumerate(rows): r['rank'] = i + 1

    return JsonResponse({'rows': rows, 'my_rank': viewer_rank, 'by': category})


# ── Activity Feed ──────────────────────────────────────────────────────────

@login_required_api
def feed(request):
    """Events from people I follow + friends + myself."""
    # collect user IDs to include
    friends = get_friends(request.user)
    following_ids = list(Follow.objects.filter(follower=request.user).values_list('following_id', flat=True))
    friend_ids    = [u.id for u in friends]
    include_ids   = set(following_ids + friend_ids + [request.user.id])

    events = ActivityEvent.objects.filter(
        user_id__in=include_ids,
        habit__is_public=True,
    ).select_related('user', 'habit', 'user__profile').prefetch_related(
        'reactions', 'comments', 'comments__user'
    )[:40]

    return JsonResponse([_event_dict(e, request.user) for e in events], safe=False)


@login_required_api
def global_feed(request):
    """Public events from all users (for discovery)."""
    events = ActivityEvent.objects.filter(
        habit__is_public=True,
        user__profile__is_public=True,
    ).select_related('user', 'habit', 'user__profile').prefetch_related(
        'reactions', 'comments', 'comments__user'
    )[:40]
    return JsonResponse([_event_dict(e, request.user) for e in events], safe=False)


# ── Reactions ──────────────────────────────────────────────────────────────

@csrf_exempt
@login_required_api
@require_http_methods(["POST"])
def toggle_reaction(request, event_id):
    body  = json.loads(request.body)
    emoji = body.get('emoji')
    if emoji not in REACTIONS:
        return JsonResponse({'error': 'Invalid emoji'}, status=400)
    try:
        event = ActivityEvent.objects.get(id=event_id)
    except ActivityEvent.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    r, created = Reaction.objects.get_or_create(event=event, user=request.user, emoji=emoji)
    if not created:
        r.delete()
        action = 'removed'
    else:
        action = 'added'

    counts = {}
    for e in REACTIONS:
        cnt = event.reactions.filter(emoji=e).count()
        if cnt: counts[e] = cnt

    return JsonResponse({'action': action, 'counts': counts})


# ── Comments ───────────────────────────────────────────────────────────────

@csrf_exempt
@login_required_api
@require_http_methods(["POST"])
def add_comment(request, event_id):
    body = json.loads(request.body)
    text = body.get('text','').strip()[:300]
    if not text:
        return JsonResponse({'error': 'Empty comment'}, status=400)
    try:
        event = ActivityEvent.objects.get(id=event_id)
    except ActivityEvent.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    c = Comment.objects.create(event=event, user=request.user, text=text)
    return JsonResponse({'ok': True, 'comment': c.to_dict()})


@csrf_exempt
@login_required_api
@require_http_methods(["DELETE"])
def delete_comment(request, comment_id):
    try:
        c = Comment.objects.get(id=comment_id, user=request.user)
        c.delete()
        return JsonResponse({'ok': True})
    except Comment.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


# ── Follow ─────────────────────────────────────────────────────────────────

@csrf_exempt
@login_required_api
@require_http_methods(["POST"])
def toggle_follow(request):
    body    = json.loads(request.body)
    user_id = body.get('user_id')
    try:
        target = User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError):
        return JsonResponse({'error': 'User not found'}, status=404)
    if target == request.user:
        return JsonResponse({'error': "Can't follow yourself"}, status=400)

    f, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        f.delete()
        return JsonResponse({'ok': True, 'action': 'unfollowed'})
    return JsonResponse({'ok': True, 'action': 'followed'})


# ── Friend requests ────────────────────────────────────────────────────────

@csrf_exempt
@login_required_api
@require_http_methods(["POST"])
def send_friend_request(request):
    body    = json.loads(request.body)
    user_id = body.get('user_id')
    try:
        to_user = User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError):
        return JsonResponse({'error': 'User not found'}, status=404)
    if to_user == request.user:
        return JsonResponse({'error': "Can't friend yourself"}, status=400)
    try:
        reverse = FriendRequest.objects.get(from_user=to_user, to_user=request.user)
        if reverse.status == 'pending':
            reverse.status = 'accepted'; reverse.save()
            return JsonResponse({'ok': True, 'status': 'accepted', 'message': "You're now friends!"})
    except FriendRequest.DoesNotExist:
        pass
    fr, created = FriendRequest.objects.get_or_create(
        from_user=request.user, to_user=to_user, defaults={'status': 'pending'}
    )
    if not created and fr.status == 'declined':
        fr.status = 'pending'; fr.save()
    return JsonResponse({'ok': True, 'status': fr.status})


@csrf_exempt
@login_required_api
@require_http_methods(["POST"])
def respond_friend_request(request):
    body   = json.loads(request.body)
    req_id = body.get('request_id')
    action = body.get('action')
    try:
        fr = FriendRequest.objects.get(id=req_id, to_user=request.user, status='pending')
    except FriendRequest.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)
    fr.status = 'accepted' if action == 'accept' else 'declined'
    fr.save()
    return JsonResponse({'ok': True, 'status': fr.status})


@csrf_exempt
@login_required_api
@require_http_methods(["POST"])
def remove_friend(request):
    body    = json.loads(request.body)
    user_id = body.get('user_id')
    try:
        other = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    FriendRequest.objects.filter(
        Q(from_user=request.user, to_user=other) | Q(from_user=other, to_user=request.user)
    ).delete()
    return JsonResponse({'ok': True})


@login_required_api
def pending_requests(request):
    reqs = FriendRequest.objects.filter(
        to_user=request.user, status='pending'
    ).select_related('from_user__profile').order_by('-created_at')
    result = []
    for fr in reqs:
        username = ''
        try: username = fr.from_user.profile.username
        except Exception: pass
        result.append({
            'request_id':   fr.id,
            'from_id':      str(fr.from_user.id),
            'username':     username,
            'display_name': fr.from_user.display_name,
            'avatar_url':   fr.from_user.avatar_url,
            'sent_at':      str(fr.created_at.date()),
        })
    return JsonResponse(result, safe=False)


@login_required_api
def friends_list(request):
    return JsonResponse([_public_profile_dict(f, viewer=request.user) for f in get_friends(request.user)], safe=False)


# ── Search & Profiles ──────────────────────────────────────────────────────

@login_required_api
def search_users(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    users = User.objects.filter(
        Q(profile__username__icontains=q) | Q(full_name__icontains=q),
        profile__is_public=True, is_verified=True,
    ).exclude(id=request.user.id).select_related('profile')[:20]
    return JsonResponse([_public_profile_dict(u, viewer=request.user) for u in users], safe=False)


@login_required_api
def public_profile(request, username):
    try:
        profile = UserProfile.objects.select_related('user').get(username=username)
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    user = profile.user
    if not profile.is_public and user != request.user:
        if not are_friends(request.user, user):
            return JsonResponse({'error': 'This profile is private'}, status=403)

    data = _public_profile_dict(user, viewer=request.user)

    # Public habits only
    habits = Habit.objects.filter(user=user, is_public=True)
    habit_list = []
    for h in habits:
        h_logs = set(HabitLog.objects.filter(habit=h).values_list('log_date', flat=True))
        s, check = 0, date.today()
        while check in h_logs: s += 1; check -= timedelta(days=1)
        habit_list.append({'name': h.name, 'icon': h.icon, 'color': h.color, 'streak': s, 'total': len(h_logs)})
    habit_list.sort(key=lambda x: x['streak'], reverse=True)
    data['habits'] = habit_list[:8]
    data['badges'] = [b.to_dict() for b in Badge.objects.filter(habit__user=user).select_related('habit').order_by('-earned_at')[:12]]

    return JsonResponse(data)


@login_required_api
def my_profile_api(request):
    if request.method == 'GET':
        profile = _ensure_profile(request.user)
        return JsonResponse({'username': profile.username, 'bio': profile.bio, 'is_public': profile.is_public})
    body    = json.loads(request.body)
    profile = _ensure_profile(request.user)
    if 'bio' in body:       profile.bio = body['bio'][:200]
    if 'is_public' in body: profile.is_public = bool(body['is_public'])
    if 'username' in body:
        new_un = body['username'].strip().lower()[:40]
        if new_un and new_un != profile.username:
            if UserProfile.objects.filter(username=new_un).exclude(pk=profile.pk).exists():
                return JsonResponse({'error': 'Username already taken'}, status=400)
            profile.username = new_un
    profile.save()
    return JsonResponse({'ok': True, 'username': profile.username})


# ── GLOBAL CHAT ────────────────────────────────────────────────────────────

@csrf_exempt
def global_chat_messages(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    if request.method == 'GET':
        since_ts = request.GET.get('since')
        qs = GlobalMessage.objects.select_related('user__profile').order_by('created_at')
        if since_ts:
            import datetime as dtlib
            try:
                since_dt = dtlib.datetime.fromtimestamp(float(since_ts), tz=dtlib.timezone.utc)
                qs = qs.filter(created_at__gt=since_dt)
            except (ValueError, OSError):
                pass
        else:
            # Initial load — last 80 messages
            qs = qs.order_by('-created_at')[:80]
            qs = list(reversed(list(qs)))
            return JsonResponse([m.to_dict() for m in qs], safe=False)
        return JsonResponse([m.to_dict() for m in qs], safe=False)

    body = json.loads(request.body)
    text = body.get('text', '').strip()[:500]
    if not text:
        return JsonResponse({'error': 'Empty message'}, status=400)
    msg = GlobalMessage.objects.create(user=request.user, text=text)
    return JsonResponse({'ok': True, 'message': msg.to_dict()}, status=201)


# ── DIRECT MESSAGES ────────────────────────────────────────────────────────

@csrf_exempt
def direct_messages(request, friend_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)

    try:
        from accounts.models import User as AccUser
        friend = AccUser.objects.get(id=friend_id)
    except Exception:
        return JsonResponse({'error': 'User not found'}, status=404)

    if request.method == 'GET':
        since_ts = request.GET.get('since')

        qs = DirectMessage.objects.filter(
            Q(sender=request.user, recipient=friend) |
            Q(sender=friend, recipient=request.user)
        ).order_by('created_at')

        if since_ts:
            # Return only messages newer than the given unix timestamp
            from django.utils.timezone import datetime as dt
            import datetime as dtlib
            try:
                since_dt = dtlib.datetime.fromtimestamp(float(since_ts), tz=dtlib.timezone.utc)
                qs = qs.filter(created_at__gt=since_dt)
            except (ValueError, OSError):
                pass
        else:
            qs = qs[:100]

        msgs = list(qs)

        # Mark received messages as read (only messages FROM friend TO me)
        DirectMessage.objects.filter(
            sender=friend, recipient=request.user, read=False
        ).update(read=True)

        return JsonResponse([m.to_dict(me=request.user) for m in msgs], safe=False)

    # POST — send a message
    body = json.loads(request.body)
    text = body.get('text', '').strip()[:500]
    if not text:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # Only friends can DM
    if not are_friends(request.user, friend):
        return JsonResponse({'error': 'You can only DM friends'}, status=403)

    msg = DirectMessage.objects.create(sender=request.user, recipient=friend, text=text)
    return JsonResponse({'ok': True, 'message': msg.to_dict(me=request.user)}, status=201)


@login_required_api
def dm_inbox(request):
    """Unread count per friend."""
    unread = DirectMessage.objects.filter(
        recipient=request.user, read=False
    ).values('sender').annotate(count=Count('id'))
    return JsonResponse({str(u['sender']): u['count'] for u in unread})


@login_required_api
def friends_for_invite(request):
    """Return current user's friends — used by challenge invite modal."""
    friends = get_friends(request.user)
    result = []
    for f in friends:
        username = ''
        try: username = f.profile.username
        except: pass
        result.append({
            'user_id':      str(f.id),
            'display_name': f.display_name,
            'avatar_url':   f.avatar_url,
            'username':     username,
            'email':        f.email,
        })
    return JsonResponse(result, safe=False)
