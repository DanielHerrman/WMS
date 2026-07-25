import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wms_core.settings")
os.environ["DJANGO_ENV"] = "production"
os.environ["ALLOWED_HOSTS"] = "localhost"
os.environ["CSRF_TRUSTED_ORIGINS"] = "http://localhost"

django.setup()

from django.test import Client
from django.contrib.auth import authenticate

# Test 1: Ověření hesla
user = authenticate(username="admin", password="Oid0MOLO95")
print(f"Authenticate admin: {'OK' if user else 'FAILED'}")

# Test 2: Login přes Client
c = Client()
resp = c.post("/admin/login/", {"username": "admin", "password": "Oid0MOLO95"})
print(f"Login POST response: {resp.status_code}")
print(f"Redirected to: {resp.get('Location', 'no redirect')}")
print(f"Login {'SUCCESS' if resp.status_code == 302 else 'FAILED'}")