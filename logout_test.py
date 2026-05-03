import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'performance_system.settings')
import django
django.setup()
from django.test import Client
from apps.accounts.models import User

c = Client()
u = User.objects.filter(is_superuser=True).first()
if u is None:
    u = User.objects.create_superuser('testadmin', 'test@example.com', 'testpass')
    print('created user')
else:
    print('found user', u.username)
login_result = c.login(username=u.username, password='testpass')
print('login', login_result)
r = c.get('/accounts/logout/')
print('status', r.status_code)
print('redirect', getattr(r, 'url', None))
print('content', r.content[:200])
