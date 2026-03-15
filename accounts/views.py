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
    """Create / replace token and send verification email."""
    EmailVerificationToken.objects.filter(user=user).delete()
    token = EmailVerificationToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(hours=24),
    )
    link = request.build_absolute_uri(f'/auth/verify-email/{token.token}/')
    try:
        send_mail(
            subject='Verify your HabitFlows email',
            message=f'Verify your email: {link}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto;background:#080810;color:#f0f0fa;padding:40px;border-radius:16px;border:1px solid #252538">
              <div style="text-align:center;margin-bottom:32px">
                <div style="display:inline-block;background:#c8ff00;border-radius:10px;padding:10px 20px">
                  <span style="font-family:sans-serif;font-size:18px;font-weight:800;color:#080810">HabitFlows</span>
                </div>
              </div>
              <h2 style="color:#c8ff00;font-size:24px;margin-bottom:12px">Verify your email</h2>
              <p style="color:#a0a0c0;line-height:1.6;margin-bottom:28px">
                Hi {user.display_name},<br/><br/>
                Click the button below to verify your email and activate your HabitFlows account.
                This link expires in <strong style="color:#f0f0fa">24 hours</strong>.
              </p>
              <a href="{link}" style="display:inline-block;background:#c8ff00;color:#080810;font-weight:700;font-size:15px;padding:14px 32px;border-radius:10px;text-decoration:none;letter-spacing:.3px">
                ✓ Verify Email
              </a>
              <p style="color:#555570;font-size:12px;margin-top:28px">
                If you didn't create this account, you can safely ignore this email.
              </p>
            </div>
            """,
            fail_silently=True,
        )
    except Exception:
        pass  # Email failure should never crash signup


def _seed_default_habits(user):
    """Give every new user a fresh copy of the 10 default habits."""
    from habits.models import Habit
    DEFAULT_HABITS = [
        {"id": "meditation", "name": "Meditation",              "icon": "🧘", "category": "Mindfulness", "color": "#a78bfa"},
        {"id": "gym",        "name": "Gym / Workout",           "icon": "💪", "category": "Fitness",     "color": "#34d399"},
        {"id": "journal",    "name": "Daily Journal",           "icon": "📓", "category": "Reflection",  "color": "#fbbf24"},
        {"id": "dsa",        "name": "DSA Practice",            "icon": "🧮", "category": "Revision",    "color": "#f87171"},
        {"id": "ds",         "name": "Data Structures",         "icon": "🗂️","category": "Revision",    "color": "#60a5fa"},
        {"id": "class",      "name": "Class Notes",             "icon": "📚", "category": "Revision",    "color": "#fb923c"},
        {"id": "reading",    "name": "Reading",                 "icon": "📖", "category": "Learning",    "color": "#e879f9"},
        {"id": "water",      "name": "Drink Water (8 glasses)", "icon": "💧", "category": "Health",      "color": "#38bdf8"},
        {"id": "sleep",      "name": "Sleep 8hrs",              "icon": "😴", "category": "Health",      "color": "#818cf8"},
        {"id": "no_social",  "name": "No Social Media",         "icon": "🚫", "category": "Mindfulness", "color": "#fb7185"},
    ]
    uid_str = str(user.id).replace('-', '')[:8]
    for h in DEFAULT_HABITS:
        Habit.objects.get_or_create(
            habit_id=f"{h['id']}_{uid_str}",
            defaults={**{k: v for k, v in h.items() if k != 'id'},
                      'user': user, 'is_default': True}
        )


# ── Pages ──────────────────────────────────────────────────────────────────

def login_page(request):
    if request.user.is_authenticated:
        return redirect('/')
    return render(request, 'accounts/auth.html', {'mode': 'login'})


def signup_page(request):
    if request.user.is_authenticated:
        return redirect('/')
    return render(request, 'accounts/auth.html', {'mode': 'signup'})


def forgot_page(request):
    return render(request, 'accounts/auth.html', {'mode': 'forgot'})


def reset_page(request, token):
    try:
        t = PasswordResetToken.objects.get(token=token)
        if not t.is_valid():
            return render(request, 'accounts/auth.html', {'mode': 'reset_expired'})
    except PasswordResetToken.DoesNotExist:
        return render(request, 'accounts/auth.html', {'mode': 'reset_expired'})
    return render(request, 'accounts/auth.html', {'mode': 'reset', 'reset_token': str(token)})


# ── API: Signup ─────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def api_signup(request):
    body = json.loads(request.body)
    email    = body.get('email', '').strip().lower()
    password = body.get('password', '')
    name     = body.get('full_name', '').strip()

    if not email or not password:
        return JsonResponse({'error': 'Email and password required.'}, status=400)
    if len(password) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters.'}, status=400)
    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'An account with this email already exists.'}, status=400)

    user = User.objects.create_user(email=email, password=password, full_name=name)
    _seed_default_habits(user)
    _send_verification_email(user, request)

    return JsonResponse({'ok': True, 'message': 'Account created! Check your email to verify.'})


# ── API: Login ──────────────────────────────────────────────────────────────

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

    if not user.is_verified:
        return JsonResponse({'error': 'Please verify your email before logging in.', 'needs_verify': True}, status=403)

    auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return JsonResponse({'ok': True, 'redirect': '/'})


# ── API: Logout ─────────────────────────────────────────────────────────────

def api_logout(request):
    auth_logout(request)
    return redirect('/auth/login/')


# ── Email Verification ──────────────────────────────────────────────────────

def verify_email(request, token):
    try:
        vt = EmailVerificationToken.objects.select_related('user').get(token=token)
    except EmailVerificationToken.DoesNotExist:
        return render(request, 'accounts/auth.html', {'mode': 'verify_invalid'})

    if not vt.is_valid():
        return render(request, 'accounts/auth.html', {'mode': 'verify_expired', 'email': vt.user.email})

    vt.user.is_verified = True
    vt.user.save()
    vt.delete()
    auth_login(request, vt.user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('/?verified=1')


@csrf_exempt
@require_http_methods(["POST"])
def resend_verification(request):
    body  = json.loads(request.body)
    email = body.get('email', '').strip().lower()
    try:
        user = User.objects.get(email=email)
        if user.is_verified:
            return JsonResponse({'error': 'Already verified.'}, status=400)
        _send_verification_email(user, request)
        return JsonResponse({'ok': True})
    except User.DoesNotExist:
        return JsonResponse({'error': 'Email not found.'}, status=404)


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

    # Generate a random 10-char temp password
    import random, string
    chars    = string.ascii_letters + string.digits + '!@#$'
    temp_pwd = ''.join(random.choices(chars, k=10))

    # Try sending email BEFORE saving password
    try:
        send_mail(
            subject='🔑 Your HabitFlows temporary password',
            message=f'Your temporary password is: {temp_pwd}\n\nLog in and change it from Profile → Security.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=f"""
            <div style="font-family:sans-serif;max-width:480px;margin:0 auto;background:#080810;color:#f0f0fa;padding:40px;border-radius:16px;border:1px solid #252538">
              <div style="text-align:center;margin-bottom:28px">
                <div style="display:inline-block;background:#c8ff00;border-radius:10px;padding:10px 20px">
                  <span style="font-size:18px;font-weight:800;color:#080810">HabitFlows</span>
                </div>
              </div>
              <div style="text-align:center;font-size:40px;margin-bottom:16px">🔑</div>
              <h2 style="color:#c8ff00;font-size:24px;margin-bottom:12px;text-align:center">Your temporary password</h2>
              <p style="color:#a0a0c0;line-height:1.6;margin-bottom:20px">
                Hi {user.display_name},<br/><br/>
                Use this temporary password to log in, then go to <strong style="color:#f0f0fa">Profile → Security</strong> to set a permanent one.
              </p>
              <div style="background:#0d0d18;border:2px solid #c8ff00;border-radius:12px;padding:20px;text-align:center;margin-bottom:24px">
                <div style="font-family:monospace;font-size:26px;font-weight:700;color:#c8ff00;letter-spacing:4px">{temp_pwd}</div>
              </div>
              <p style="color:#555570;font-size:12px;text-align:center">
                If you didn't request this, log in immediately and change your password.
              </p>
            </div>
            """,
        )
    except Exception as e:
        return JsonResponse({'error': 'Could not send email. Please check your email address or try again later.'}, status=500)

    # Email sent — now save the new password
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
        rt = PasswordResetToken.objects.select_related('user').get(token=token)
    except PasswordResetToken.DoesNotExist:
        return JsonResponse({'error': 'Invalid or expired link.'}, status=400)

    if not rt.is_valid():
        return JsonResponse({'error': 'This link has expired. Please request a new one.'}, status=400)

    rt.user.set_password(password)
    rt.user.save()
    rt.used = True
    rt.save()
    return JsonResponse({'ok': True, 'message': 'Password updated! You can now log in.'})


# ── Google OAuth ────────────────────────────────────────────────────────────

def google_login(request):
    """Redirect user to Google's OAuth consent screen."""
    params = urllib.parse.urlencode({
        'client_id':     settings.GOOGLE_CLIENT_ID,
        'redirect_uri':  request.build_absolute_uri('/auth/google/callback/'),
        'response_type': 'code',
        'scope':         'openid email profile',
        'access_type':   'online',
        'prompt':        'select_account',
    })
    return HttpResponseRedirect(f'https://accounts.google.com/o/oauth2/v2/auth?{params}')


def google_callback(request):
    """Handle Google's redirect back with auth code."""
    code  = request.GET.get('code')
    error = request.GET.get('error')

    if error or not code:
        return redirect('/auth/login/?error=google_cancelled')

    # Exchange code for tokens
    token_url = 'https://oauth2.googleapis.com/token'
    token_data = urllib.parse.urlencode({
        'code':          code,
        'client_id':     settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri':  request.build_absolute_uri('/auth/google/callback/'),
        'grant_type':    'authorization_code',
    }).encode()

    try:
        req  = urllib.request.Request(token_url, data=token_data, method='POST')
        resp = urllib.request.urlopen(req, timeout=10)
        token_json = json.loads(resp.read())
    except Exception:
        return redirect('/auth/login/?error=google_failed')

    # Get user info
    access_token = token_json.get('access_token')
    try:
        info_req  = urllib.request.Request(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        info_resp = urllib.request.urlopen(info_req, timeout=10)
        info      = json.loads(info_resp.read())
    except Exception:
        return redirect('/auth/login/?error=google_failed')

    google_id  = info.get('sub')
    email      = info.get('email', '').lower()
    name       = info.get('name', '')
    avatar     = info.get('picture', '')

    # Find or create user
    user = None
    try:
        user = User.objects.get(google_id=google_id)
    except User.DoesNotExist:
        try:
            user = User.objects.get(email=email)
            user.google_id   = google_id
            user.avatar_url  = avatar
            user.is_verified = True
            if not user.full_name:
                user.full_name = name
            user.save()
        except User.DoesNotExist:
            user = User.objects.create_user(
                email=email, full_name=name,
                avatar_url=avatar, google_id=google_id,
                is_verified=True,
            )
            _seed_default_habits(user)

    auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('/')


# ── ADD / CHANGE PASSWORD (for profile settings) ───────────────────────────

@csrf_exempt
def api_add_password(request):
    """Google OAuth users who have no password can set one here."""
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
        # Already has password — require current password to change
        current = body.get('current_password', '')
        if not current:
            return JsonResponse({'error': 'Current password required to change it'}, status=400)
        if not user.check_password(current):
            return JsonResponse({'error': 'Current password is incorrect'}, status=400)

    user.set_password(new_password)
    user.save()
    # Re-login so session stays valid after password change
    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request, user)
    return JsonResponse({'ok': True, 'message': 'Password set successfully'})


@csrf_exempt
def api_account_info(request):
    """Return account info — specifically whether the user has a password set."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Login required'}, status=401)
    return JsonResponse({
        'has_password':  request.user.has_usable_password(),
        'has_google':    bool(request.user.google_id),
        'email':         request.user.email,
        'display_name':  request.user.display_name,
    })
