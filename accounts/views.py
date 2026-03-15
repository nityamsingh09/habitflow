import json
import uuid
import urllib.request
import urllib.parse
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import User, EmailVerificationToken, PasswordResetToken


# ── Helpers ────────────────────────────────────────────────────────────────

def _send_verification_email(user, request):
    EmailVerificationToken.objects.filter(user=user).delete()
    token = EmailVerificationToken.objects.create(
        user=user, expires_at=timezone.now() + timedelta(hours=24),
    )
    link = request.build_absolute_uri(f'/auth/verify-email/{token.token}/')
    try:
        send_mail(
            subject='Verify your HabitFlows email',
            message=f'Verify your HabitFlows account: {link}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto;background:#080810;color:#f0f0fa;padding:40px;border-radius:16px;border:1px solid #252538">
              <div style="text-align:center;margin-bottom:32px">
                <div style="display:inline-block;background:#c8ff00;border-radius:10px;padding:10px 20px">
                  <span style="font-size:18px;font-weight:800;color:#080810">HabitFlows</span>
                </div>
              </div>
              <h2 style="color:#c8ff00;font-size:24px;margin-bottom:12px">Verify your email</h2>
              <p style="color:#a0a0c0;line-height:1.6;margin-bottom:28px">
                Hi {user.display_name},<br/><br/>
                Click the button below to verify your email and activate your HabitFlows account.
                This link expires in <strong style="color:#f0f0fa">24 hours</strong>.
              </p>
              <a href="{link}" style="display:inline-block;background:#c8ff00;color:#080810;font-weight:700;font-size:15px;padding:14px 32px;border-radius:10px;text-decoration:none;letter-spacing:.3px">
                &#10003; Verify Email
              </a>
              <p style="color:#555570;font-size:12px;margin-top:28px">
                If you didn't create this account, you can safely ignore this email.
              </p>
            </div>
            """,
            fail_silently=True,
        )
    except Exception:
        pass


def _seed_default_habits(user):
    """Give every new user a fresh copy of the 10 default habits."""
    from habits.models import Habit
    defaults = [
        {'name': 'Morning Run',        'icon': '🏃', 'category': 'Fitness',      'color': '#f97316'},
        {'name': 'Read 30 Minutes',    'icon': '📚', 'category': 'Learning',     'color': '#c8ff00'},
        {'name': 'Meditate',           'icon': '🧘', 'category': 'Mindfulness',  'color': '#a78bfa'},
        {'name': 'Drink Water',        'icon': '💧', 'category': 'Health',       'color': '#60a5fa'},
        {'name': 'Journaling',         'icon': '📓', 'category': 'Reflection',   'color': '#fbbf24'},
    ]
    for d in defaults:
        hid = f"default_{str(user.id).replace('-','')[:8]}_{d['name'].lower().replace(' ','_')}"
        Habit.objects.get_or_create(
            habit_id=hid, user=user,
            defaults={**d, 'is_default': True},
        )


# ── Auth pages ─────────────────────────────────────────────────────────────

def login_page(request):
    error = request.GET.get('error', '')
    return render(request, 'accounts/auth.html', {'mode': 'login', 'error': error})

def signup_page(request):
    return render(request, 'accounts/auth.html', {'mode': 'signup'})

def forgot_page(request):
    return render(request, 'accounts/auth.html', {'mode': 'forgot'})

def reset_page(request, token):
    try:
        rt = PasswordResetToken.objects.get(token=token)
        if rt.used or rt.expires_at < timezone.now():
            return render(request, 'accounts/auth.html', {'mode': 'reset_expired'})
    except PasswordResetToken.DoesNotExist:
        return render(request, 'accounts/auth.html', {'mode': 'reset_expired'})
    return render(request, 'accounts/auth.html', {'mode': 'reset', 'reset_token': str(token)})


# ── API ────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_signup(request):
    body     = json.loads(request.body)
    email    = body.get('email', '').strip().lower()
    password = body.get('password', '')
    name     = body.get('name', '').strip() or email.split('@')[0]

    if not email or not password:
        return JsonResponse({'error': 'Email and password required.'}, status=400)
    if len(password) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters.'}, status=400)
    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'An account with this email already exists.'}, status=400)

    user = User.objects.create_user(email=email, password=password, full_name=name)
    _seed_default_habits(user)
    _send_verification_email(user, request)
    auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return JsonResponse({'ok': True, 'redirect': '/'})


@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    body     = json.loads(request.body)
    email    = body.get('email', '').strip().lower()
    password = body.get('password', '')
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Invalid email or password.'}, status=401)
    if not user.check_password(password):
        return JsonResponse({'error': 'Invalid email or password.'}, status=401)
    auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return JsonResponse({'ok': True, 'redirect': '/'})


def api_logout(request):
    auth_logout(request)
    return redirect('/auth/login/')


def verify_email(request, token):
    try:
        vt = EmailVerificationToken.objects.get(token=token)
        if vt.expires_at < timezone.now():
            return redirect('/auth/login/?error=expired')
        vt.user.is_verified = True
        vt.user.save(update_fields=['is_verified'])
        vt.delete()
        return redirect('/?verified=1')
    except EmailVerificationToken.DoesNotExist:
        return redirect('/auth/login/?error=invalid')


@csrf_exempt
@require_http_methods(["POST"])
def resend_verification(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)
    _send_verification_email(request.user, request)
    return JsonResponse({'ok': True})


# ── Forgot / Reset Password ─────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_forgot(request):
    body  = json.loads(request.body)
    email = body.get('email', '').strip().lower()
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({'ok': True})  # don't reveal existence

    import random, string
    chars    = string.ascii_letters + string.digits + '!@#$'
    temp_pwd = ''.join(random.choices(chars, k=10))

    try:
        send_mail(
            subject='Your HabitFlows temporary password',
            message=f'Your temporary password is: {temp_pwd}\n\nLog in and go to Profile > Security to set a permanent password.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto;background:#080810;color:#f0f0fa;padding:40px;border-radius:16px;border:1px solid #252538">
              <div style="text-align:center;margin-bottom:28px">
                <div style="display:inline-block;background:#c8ff00;border-radius:10px;padding:10px 20px">
                  <span style="font-size:18px;font-weight:800;color:#080810">HabitFlows</span>
                </div>
              </div>
              <div style="text-align:center;font-size:40px;margin-bottom:16px">&#128273;</div>
              <h2 style="color:#c8ff00;font-size:24px;margin-bottom:12px;text-align:center">Your temporary password</h2>
              <p style="color:#a0a0c0;line-height:1.6;margin-bottom:20px">
                Hi {user.display_name},<br/><br/>
                Use this to log in, then set a permanent password from <strong style="color:#f0f0fa">Profile &rarr; Security</strong>.
              </p>
              <div style="background:#0d0d18;border:2px solid #c8ff00;border-radius:12px;padding:20px;text-align:center;margin-bottom:24px">
                <div style="font-family:monospace;font-size:28px;font-weight:700;color:#c8ff00;letter-spacing:6px">{temp_pwd}</div>
              </div>
              <p style="color:#555570;font-size:12px;text-align:center">
                If you didn't request this, log in and change your password immediately.
              </p>
            </div>
            """,
        )
    except Exception as e:
        return JsonResponse({'error': f'Could not send email. ({e})'}, status=500)

    user.set_password(temp_pwd)
    user.save()
    return JsonResponse({'ok': True})


@csrf_exempt
@require_http_methods(["POST"])
def api_reset_password(request):
    body     = json.loads(request.body)
    token    = body.get('token', '')
    password = body.get('password', '')
    if len(password) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters.'}, status=400)
    try:
        rt = PasswordResetToken.objects.get(token=token, used=False)
        if rt.expires_at < timezone.now():
            return JsonResponse({'error': 'Reset link has expired.'}, status=400)
    except PasswordResetToken.DoesNotExist:
        return JsonResponse({'error': 'Invalid or expired reset link.'}, status=400)
    rt.user.set_password(password)
    rt.user.save()
    rt.used = True
    rt.save()
    return JsonResponse({'ok': True})


# ── Add / Change Password ───────────────────────────────────────────────────

@csrf_exempt
def api_add_password(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    body = json.loads(request.body)
    new_password = body.get('new_password', '')
    if len(new_password) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters'}, status=400)
    user = request.user
    if user.has_usable_password():
        current = body.get('current_password', '')
        if not current:
            return JsonResponse({'error': 'Current password required to change it'}, status=400)
        if not user.check_password(current):
            return JsonResponse({'error': 'Current password is incorrect'}, status=400)
    user.set_password(new_password)
    user.save()
    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request, user)
    return JsonResponse({'ok': True, 'message': 'Password set successfully'})


@csrf_exempt
def api_account_info(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)
    return JsonResponse({
        'has_password': request.user.has_usable_password(),
        'has_google':   bool(request.user.google_id),
        'email':        request.user.email,
        'display_name': request.user.display_name,
    })


# ── Google OAuth ───────────────────────────────────────────────────────────

def google_login(request):
    params = {
        'client_id':     settings.GOOGLE_CLIENT_ID,
        'redirect_uri':  request.build_absolute_uri('/auth/google/callback/'),
        'response_type': 'code',
        'scope':         'openid email profile',
        'access_type':   'offline',
        'prompt':        'select_account',
    }
    return HttpResponseRedirect(
        f'https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}'
    )


def google_callback(request):
    code  = request.GET.get('code')
    error = request.GET.get('error')
    if error or not code:
        return redirect('/auth/login/?error=google_cancelled')

    # Exchange code for tokens
    token_data = urllib.parse.urlencode({
        'code':          code,
        'client_id':     settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri':  request.build_absolute_uri('/auth/google/callback/'),
        'grant_type':    'authorization_code',
    }).encode()
    try:
        req  = urllib.request.Request('https://oauth2.googleapis.com/token',
                                      data=token_data, method='POST')
        resp = urllib.request.urlopen(req, timeout=10)
        tokens = json.loads(resp.read().decode())
    except Exception:
        return redirect('/auth/login/?error=google_failed')

    # Fetch user info
    try:
        req2     = urllib.request.Request(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f"Bearer {tokens['access_token']}"}
        )
        resp2    = urllib.request.urlopen(req2, timeout=10)
        ginfo    = json.loads(resp2.read().decode())
    except Exception:
        return redirect('/auth/login/?error=google_failed')

    gemail  = ginfo.get('email', '').lower()
    gname   = ginfo.get('name', gemail.split('@')[0])
    gsub    = ginfo.get('sub', '')
    gavatar = ginfo.get('picture', '')

    # Find or create user
    user = None
    try:
        user = User.objects.get(google_id=gsub)
    except User.DoesNotExist:
        pass
    if not user:
        try:
            user = User.objects.get(email=gemail)
            if not user.google_id:
                user.google_id  = gsub
                user.avatar_url = gavatar or user.avatar_url
                user.save(update_fields=['google_id', 'avatar_url'])
        except User.DoesNotExist:
            user = User.objects.create(
                email=gemail, full_name=gname,
                google_id=gsub, avatar_url=gavatar,
                is_verified=True,
            )
            user.set_unusable_password()
            user.save()
            _seed_default_habits(user)

    auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('/')
