import django, os, sys, traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wms_core.settings")
os.environ["DJANGO_ENV"] = "production"
os.environ["ALLOWED_HOSTS"] = "localhost"
os.environ["CSRF_TRUSTED_ORIGINS"] = "http://localhost"

django.setup()

from django.test import RequestFactory
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import AnonymousUser

rf = RequestFactory()
r = rf.get("/admin/login/")
r.user = AnonymousUser()

try:
    resp = LoginView.as_view()(r)
    print("STATUS:", resp.status_code)
except Exception as e:
    traceback.print_exc()