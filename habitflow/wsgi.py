import os
import sys
from pathlib import Path

# Ensure the project root is on the path so Django can find all apps
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'habitflow.settings')

from django.core.wsgi import get_wsgi_application
app = get_wsgi_application()          # Vercel looks for "app"
application = app                     # gunicorn / local looks for "application"
