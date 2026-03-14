from django.urls import path
from . import views

urlpatterns = [
    path('api/subscription',          views.subscription_status, name='subscription_status'),
    path('api/subscription/order',    views.create_order,        name='create_order'),
    path('api/subscription/verify',   views.verify_payment,      name='verify_payment'),
    path('api/subscription/cancel',   views.cancel_subscription, name='cancel_subscription'),
]
