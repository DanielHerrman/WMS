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
u.set_password("Oid0MOLO95")
u.save()
print("Password reset to Oid0MOLO95 - OK")

# Verify
from django.contrib.auth import authenticate
user = authenticate(username="admin", password="Oid0MOLO95")
print(f"Authenticate admin: {'OK' if user else 'FAILED'}")
