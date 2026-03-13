from django.urls import path
from . import views

urlpatterns = [
    # Pages
    path('login/',                     views.login_page,         name='login'),
    path('signup/',                    views.signup_page,        name='signup'),
    path('forgot-password/',           views.forgot_page,        name='forgot'),
    path('reset-password/<uuid:token>/',views.reset_page,        name='reset'),
    path('logout/',                    views.api_logout,         name='logout'),

    # Email verification
    path('verify-email/<uuid:token>/', views.verify_email,       name='verify_email'),

    # API
    path('api/signup',                 views.api_signup,         name='api_signup'),
    path('api/login',                  views.api_login,          name='api_login'),
    path('api/forgot',                 views.api_forgot,         name='api_forgot'),
    path('api/reset-password',         views.api_reset_password, name='api_reset_password'),
    path('api/resend-verification',    views.resend_verification,name='resend_verification'),

    # Google OAuth
    path('google/',                    views.google_login,       name='google_login'),
    path('google/callback/',           views.google_callback,    name='google_callback'),
]
