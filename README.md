# HabitFlows — Django + Auth + Google OAuth

Full-featured habit tracker with email/password signup, email verification,
Google OAuth "Continue with Google", password reset, and per-user data isolation.

---

## Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000 — you'll land on the login page.

---

## Features

| Feature | Detail |
|---|---|
| Email signup | Password hashed with Django's PBKDF2, min 8 chars |
| Email verification | 24-hour link sent via Gmail SMTP |
| Google OAuth | One-click login via Google account |
| Forgot password | 2-hour reset link sent to email |
| Per-user habits | Every user gets their own private habit data |
| Session auth | 30-day login cookie |

---

## Google OAuth Setup (Required for "Continue with Google")

1. Go to https://console.cloud.google.com/
2. Create a project → **APIs & Services** → **Credentials**
3. **Create OAuth 2.0 Client ID** → Web application
4. Add Authorised redirect URI:
   - `http://127.0.0.1:8000/auth/google/callback/`  (dev)
   - `https://yourdomain.com/auth/google/callback/`  (production)
5. Copy **Client ID** and **Client Secret** into `settings.py`:

```python
GOOGLE_CLIENT_ID     = 'xxxx.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'GOCSPX-xxxx'
```

---

## Email Configuration (already set)

```python
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = 'habitflowsw@gmail.com'
EMAIL_HOST_PASSWORD = 'amol agkr wcvx xjvh'   # Gmail App Password
DEFAULT_FROM_EMAIL  = 'HabitFlows <habitflowsw@gmail.com>'
```

Make sure "Less secure app access" is OFF and you're using a Gmail **App Password**
(not your regular Gmail password). App passwords work even with 2FA enabled.

---

## Auth URL Map

| URL | Page |
|---|---|
| `/auth/login/` | Sign in |
| `/auth/signup/` | Create account |
| `/auth/forgot-password/` | Forgot password |
| `/auth/reset-password/<token>/` | Reset password |
| `/auth/verify-email/<token>/` | Email verification landing |
| `/auth/logout/` | Sign out |
| `/auth/google/` | Initiate Google OAuth |
| `/auth/google/callback/` | Google OAuth callback |

---

## Project Structure

```
habitflows/
├── manage.py
├── db.sqlite3              ← auto-created on migrate
├── requirements.txt
├── habitflows/
│   ├── settings.py         ← email + Google OAuth config here
│   └── urls.py
├── accounts/               ← NEW: auth app
│   ├── models.py           ← User, EmailVerificationToken, PasswordResetToken
│   ├── views.py            ← signup, login, verify, google oauth, forgot/reset
│   ├── urls.py
│   ├── migrations/
│   └── templates/accounts/
│       └── auth.html       ← beautiful split-panel auth page
└── habits/
    ├── models.py           ← Habit (user FK), HabitLog, Badge
    ├── views.py            ← all routes guarded by @login_required_api/page
    ├── urls.py
    └── templates/habits/
        └── index.html      ← user profile card + logout in sidebar
```

---

## Production Checklist

- [ ] Replace `SECRET_KEY` with a real random key (use `django-environ`)  
- [ ] Set `DEBUG = False`  
- [ ] Set `ALLOWED_HOSTS = ['yourdomain.com']`  
- [ ] Add production Google OAuth redirect URI in Cloud Console  
- [ ] Use PostgreSQL instead of SQLite  
- [ ] Serve static files via whitenoise or nginx  
