# apps/students/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Student


@login_required
def student_list(request):
    """Only admin/teacher can view the full student list."""
    if not (request.user.is_superuser or getattr(request.user, 'role', None) in ['admin', 'teacher']):
        raise PermissionDenied("You do not have permission to view the student list.")
    students = Student.objects.all()
    return render(request, 'students/list.html', {'students': students})
