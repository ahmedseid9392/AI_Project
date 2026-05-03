import django
from django.template import libraries
print('Django', django.get_version())
print('static json_script', 'json_script' in libraries['static'].tags)
print('json_script library exists', 'json_script' in libraries)
