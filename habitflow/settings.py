from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-habitflow-change-this-in-production-use-env-var'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    # Django core — order matters: auth must come before our custom user model app
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    # Project apps
    'accounts',
    'habits',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]

ROOT_URLCONF = 'habitflow.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
            ],
        },
    },
]

WSGI_APPLICATION = 'habitflow.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_USER_MODEL = 'accounts.User'

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30   # 30 days
SESSION_COOKIE_HTTPONLY = True

STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Email (Gmail SMTP) ──────────────────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = 'habitfloww@gmail.com'
EMAIL_HOST_PASSWORD = 'amol agkr wcvx xjvh'
DEFAULT_FROM_EMAIL  = 'HabitFlow <habitfloww@gmail.com>'

# ── Google OAuth ─────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID     = '65650647695-dsoilitqu0p95t7ago0t7ijq5vtc07s2.apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = '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'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]
