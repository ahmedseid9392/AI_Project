import json

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count

from apps.students.models import Student
from apps.predictions.models import Prediction


@login_required
def dashboard(request):
    user = request.user
    is_staff = user.is_superuser or getattr(user, 'role', None) in ['admin', 'teacher']

    context = {}

    if is_staff:
        # Admin/Teacher dashboard — full stats
        total_students = Student.objects.count()
        total_predictions = Prediction.objects.count()
        evaluated_predictions = Prediction.objects.filter(is_accurate__isnull=False)
        model_accuracy = None
        if evaluated_predictions.exists():
            accurate_count = evaluated_predictions.filter(is_accurate=True).count()
            model_accuracy = round((accurate_count / evaluated_predictions.count()) * 100, 1)

        at_risk_students = Student.objects.filter(current_grade__in=['D', 'F']).count()
        grade_distribution = (
            Student.objects.exclude(current_grade__isnull=True)
            .values('current_grade')
            .annotate(count=Count('id'))
            .order_by('current_grade')
        )
        grade_labels = [item['current_grade'] for item in grade_distribution]
        grade_data = [item['count'] for item in grade_distribution]
        recent_predictions = Prediction.objects.select_related('student').all()[:5]

        context.update({
            'total_students': total_students,
            'total_predictions': total_predictions,
            'model_accuracy': model_accuracy,
            'at_risk_students': at_risk_students,
            'grade_labels': grade_labels,
            'grade_data': grade_data,
            'grade_labels_json': json.dumps(grade_labels),
            'grade_data_json': json.dumps(grade_data),
            'recent_predictions': recent_predictions,
        })
    else:
        # Student dashboard — only their own data
        student_profile = None
        student_predictions = []
        try:
            student_profile = Student.objects.get(user=user)
            student_predictions = Prediction.objects.filter(student=student_profile)[:5]
        except Student.DoesNotExist:
            pass

        context.update({
            'student_profile': student_profile,
            'student_predictions': student_predictions,
        })

    return render(request, 'dashboard.html', context)
