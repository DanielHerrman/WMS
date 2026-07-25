import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wms_core.settings")
os.environ["DJANGO_ENV"] = "production"
os.environ["ALLOWED_HOSTS"] = "localhost"
os.environ["CSRF_TRUSTED_ORIGINS"] = "http://localhost"

django.setup()

from django.contrib.auth.models import User

# Reset password first
u = User.objects.get(username="admin")
u.set_password("***REMOVED***")
u.save()
print("Password reset to ***REMOVED*** - OK")

# Verify
from django.contrib.auth import authenticate
user = authenticate(username="admin", password="***REMOVED***")
print(f"Authenticate admin: {'OK' if user else 'FAILED'}")
