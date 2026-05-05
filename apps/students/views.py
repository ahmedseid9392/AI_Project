# apps/students/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import models

from .models import Student


@login_required
def student_list(request):
    """Only admin/teacher can view the full student list."""
    if not (request.user.is_superuser or getattr(request.user, 'role', None) in ['admin', 'teacher']):
        raise PermissionDenied("You do not have permission to view the student list.")

    students = Student.objects.prefetch_related('predictions').annotate(prediction_count=models.Count('predictions')).order_by('student_id')

    search_query = request.GET.get('q', '').strip()
    selected_grade = request.GET.get('grade', '')
    selected_internet = request.GET.get('internet', '')
    selected_activities = request.GET.get('activities', '')

    if search_query:
        students = students.filter(
            models.Q(student_id__icontains=search_query) |
            models.Q(first_name__icontains=search_query) |
            models.Q(last_name__icontains=search_query) |
            models.Q(email__icontains=search_query)
        )

    if selected_grade:
        students = students.filter(current_grade=selected_grade)

    if selected_internet in ['yes', 'no']:
        students = students.filter(internet_access_at_home=(selected_internet == 'yes'))

    if selected_activities in ['yes', 'no']:
        students = students.filter(extracurricular_activities=(selected_activities == 'yes'))

    paginator = Paginator(students, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Add latest prediction info for visible students only
    for student in page_obj.object_list:
        if student.prediction_count > 0:
            student.latest_prediction = student.predictions.first()
        else:
            student.latest_prediction = None

    context = {
        'students': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'search_query': search_query,
        'selected_grade': selected_grade,
        'selected_internet': selected_internet,
        'selected_activities': selected_activities,
    }

    return render(request, 'students/list.html', context)
