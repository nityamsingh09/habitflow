import json
import hmac
import hashlib
import base64
import urllib.request
import urllib.parse
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Subscription, get_or_create_subscription

RAZORPAY_KEY_ID     = getattr(settings, 'RAZORPAY_KEY_ID',     'rzp_test_SR5knhi5sGaNi1')
RAZORPAY_KEY_SECRET = getattr(settings, 'RAZORPAY_KEY_SECRET',  'nz0s1s4CHvRrZmGEZ4Hcvw6H')

PLAN_PRICES = {
    'monthly': {'amount': 2900,  'currency': 'INR', 'label': '₹29/month'},
    'yearly':  {'amount': 29900, 'currency': 'INR', 'label': '₹299/year'},
}


def login_required_api(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Login required'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def _razorpay_create_order(amount, currency, notes):
    """Create Razorpay order using urllib — no extra package needed."""
    url  = 'https://api.razorpay.com/v1/orders'
    data = json.dumps({
        'amount':          amount,
        'currency':        currency,
        'payment_capture': 1,          # auto-capture on payment
        'notes':           notes,
    }).encode()
    creds = base64.b64encode(f'{RAZORPAY_KEY_ID}:{RAZORPAY_KEY_SECRET}'.encode()).decode()
    req   = urllib.request.Request(
        url, data=data,
        headers={'Content-Type': 'application/json', 'Authorization': f'Basic {creds}'},
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


@login_required_api
def subscription_status(request):
    sub = get_or_create_subscription(request.user)
    return JsonResponse(sub.to_dict())


@csrf_exempt
@login_required_api
@require_http_methods(['POST'])
def create_order(request):
    """Create a real Razorpay order and return order_id to frontend."""
    body = json.loads(request.body)
    plan = body.get('plan', 'monthly')
    if plan not in PLAN_PRICES:
        return JsonResponse({'error': 'Invalid plan'}, status=400)

    price = PLAN_PRICES[plan]
    try:
        order = _razorpay_create_order(
            amount=price['amount'],
            currency=price['currency'],
            notes={'plan': plan, 'user_id': str(request.user.id)},
        )
        return JsonResponse({
            'order_id':   order['id'],
            'amount':     price['amount'],
            'currency':   price['currency'],
            'key_id':     RAZORPAY_KEY_ID,
            'plan':       plan,
            'user_name':  request.user.display_name,
            'user_email': request.user.email,
        })
    except Exception as e:
        return JsonResponse({'error': f'Could not create order: {e}'}, status=500)


@csrf_exempt
@login_required_api
@require_http_methods(['POST'])
def verify_payment(request):
    """Verify Razorpay payment signature and activate subscription."""
    body        = json.loads(request.body)
    payment_id  = body.get('razorpay_payment_id', '')
    order_id    = body.get('razorpay_order_id', '')
    signature   = body.get('razorpay_signature', '')
    plan        = body.get('plan', 'monthly')

    # Verify HMAC-SHA256 signature
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        f'{order_id}|{payment_id}'.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return JsonResponse({'error': 'Invalid payment signature'}, status=400)

    # Activate subscription
    sub = get_or_create_subscription(request.user)
    sub.plan = plan
    sub.is_active = True
    sub.razorpay_payment_id = payment_id
    sub.razorpay_order_id   = order_id
    sub.expires_at = timezone.now() + (timedelta(days=30) if plan == 'monthly' else timedelta(days=365))
    sub.save()
    return JsonResponse({'ok': True, 'subscription': sub.to_dict()})


@csrf_exempt
@login_required_api
def cancel_subscription(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    sub = get_or_create_subscription(request.user)
    sub.plan      = Subscription.PLAN_FREE
    sub.expires_at = None
    sub.is_active  = True
    sub.save()
    return JsonResponse({'ok': True})
