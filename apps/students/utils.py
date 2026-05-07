from django.contrib.auth import get_user_model

from .models import Student


def _generate_student_id(user_id):
    base_student_id = f"REG{user_id:04d}"
    student_id = base_student_id
    suffix = 1

    while Student.objects.filter(student_id=student_id).exists():
        student_id = f"{base_student_id}-{suffix}"
        suffix += 1

    return student_id


def ensure_student_profile_for_user(user):
    if getattr(user, 'role', None) != 'student':
        return None

    student = Student.objects.filter(user=user).first()
    if student:
        return student

    first_name = (user.first_name or '').strip() or user.username
    last_name = (user.last_name or '').strip() or 'Student'
    email = (user.email or '').strip() or f'{user.username}@example.com'

    return Student.objects.create(
        user=user,
        student_id=_generate_student_id(user.id),
        first_name=first_name,
        last_name=last_name,
        email=email,
        attendance_percentage=0,
        previous_grade=0,
        study_time=0,
        failures_past=0,
        family_support=0,
        extracurricular_activities=False,
        internet_access_at_home=True,
        parent_education_level=5,
    )


def ensure_registered_student_profiles():
    User = get_user_model()

    for user in User.objects.filter(role='student'):
        ensure_student_profile_for_user(user)


def registered_student_queryset():
    ensure_registered_student_profiles()
    return Student.objects.filter(user__isnull=False, user__role='student')
