import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wms_core.settings")
os.environ["DJANGO_ENV"] = "production"
os.environ["ALLOWED_HOSTS"] = "localhost"

django.setup()

from django.contrib.auth.models import User

users = User.objects.all()
print(f"Total users: {users.count()}")
for u in users:
    print(f"  username={u.username}, is_superuser={u.is_superuser}, is_staff={u.is_staff}, is_active={u.is_active}")