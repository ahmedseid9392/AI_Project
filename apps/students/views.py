# apps/students/views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage
from django.db import models

from .forms import RegisteredStudentUpdateForm
from .utils import registered_student_queryset


def _require_staff_user(user):
    if not (user.is_superuser or getattr(user, 'role', None) in ['admin', 'teacher']):
        raise PermissionDenied("You do not have permission to manage student records.")


@login_required
def student_list(request):
    """Only admin/teacher can view the full student list."""
    _require_staff_user(request.user)

    students = (
        registered_student_queryset()
        .select_related('user')
        .prefetch_related('predictions')
        .annotate(prediction_count=models.Count('predictions'))
        .order_by('student_id')
    )

    paginator = Paginator(students, 10)
    page_number = request.GET.get('page')

    try:
        page_obj = paginator.get_page(page_number)
    except EmptyPage:
        # Fallback if the page number is less than 1 or out of range
        page_obj = paginator.page(1)

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
    }

    return render(request, 'students/list.html', context)


@login_required
def edit_registered_student(request, pk):
    _require_staff_user(request.user)
    student = get_object_or_404(registered_student_queryset().select_related('user'), pk=pk)

    if request.method == 'POST':
        form = RegisteredStudentUpdateForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student and linked user updated successfully.')
            return redirect('students:student_list')
    else:
        form = RegisteredStudentUpdateForm(instance=student)

    return render(request, 'students/edit.html', {'form': form, 'student': student})


@login_required
def delete_registered_student(request, pk):
    _require_staff_user(request.user)
    student = get_object_or_404(registered_student_queryset().select_related('user'), pk=pk)

    if request.method == 'POST':
        linked_user = student.user
        display_name = student.get_full_name()
        if linked_user:
            linked_user.delete()
        else:
            student.delete()
        messages.success(request, f'{display_name} was deleted successfully.')
    return redirect('students:student_list')
