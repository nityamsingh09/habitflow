"""
Email via Resend HTTP API.

ERROR 1010 fix:
- onboarding@resend.dev only works when recipient = your Resend account email
- Solution: use Resend's API with 'to' set to recipient but 'reply_to' set properly
- Real fix: add a verified domain OR verified email address in Resend dashboard

For testing without a domain:
1. Go to resend.com → Emails → select "Send test email"
2. OR go to resend.com → Settings → add your gmail as a verified sender email
   Then set RESEND_FROM_EMAIL=nityamsingh2005@gmail.com in env vars
"""
import json
import urllib.request
import urllib.error
import logging

logger = logging.getLogger(__name__)


def send_email(to_email, subject, html_body, text_body=''):
    """
    Send via Resend HTTP API.
    Returns (success: bool, error_message: str)
    """
    from django.conf import settings

    api_key = getattr(settings, 'RESEND_API_KEY', '').strip()

    if not api_key:
        print(f'\n[EMAIL - no API key]\nTo: {to_email}\nSubject: {subject}\n{text_body}\n')
        return True, ''

    # From address — must be a verified domain/email in your Resend account
    # Default: onboarding@resend.dev (only works if recipient = your Resend signup email)
    # Fix: set RESEND_FROM_EMAIL env var to a verified address
    from_addr = getattr(settings, 'RESEND_FROM_EMAIL', 'onboarding@resend.dev')

    payload = {
        'from':    from_addr,
        'to':      [to_email],
        'subject': subject,
        'html':    html_body,
    }
    if text_body:
        payload['text'] = text_body

    data = json.dumps(payload).encode('utf-8')
    req  = urllib.request.Request(
        'https://api.resend.com/emails',
        data=data,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type':  'application/json',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            print(f'[RESEND OK] id={result.get("id")} to={to_email}')
            return True, ''
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        print(f'[RESEND ERROR] HTTP {e.code}: {raw}')
        try:
            err  = json.loads(raw)
            code = err.get('statusCode') or e.code
            name = err.get('name', '')
            msg  = err.get('message', raw)

            # Friendly messages for known Resend error codes
            friendly = {
                1010: (
                    'From address not verified. '
                    'Go to resend.com → Domains → add your domain, '
                    'OR in Resend settings add a verified sender email, '
                    'then set RESEND_FROM_EMAIL env var on Render.'
                ),
                1002: 'Invalid API key. Check RESEND_API_KEY on Render.',
                1004: 'Invalid recipient email address.',
            }
            user_msg = friendly.get(code, f'{name}: {msg}')
        except Exception:
            user_msg = raw
        return False, user_msg
    except Exception as e:
        print(f'[RESEND NETWORK ERROR] {e}')
        return False, str(e)
