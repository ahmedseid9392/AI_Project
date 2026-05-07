import json

from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg

from apps.students.models import Student
from apps.students.utils import ensure_student_profile_for_user, registered_student_queryset
from apps.predictions.models import Prediction
from apps.predictions.ml_model import performance_model


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    return render(request, 'landing.html')


@login_required
def dashboard(request):
    user = request.user
    is_staff = user.is_superuser or getattr(user, 'role', None) in ['admin', 'teacher']

    context = {}

    if is_staff:
        # Admin/Teacher dashboard — full stats
        registered_students = registered_student_queryset()
        total_students = registered_students.count()
        total_predictions = Prediction.objects.count()
        evaluated_predictions = Prediction.objects.filter(is_accurate__isnull=False)
        model_accuracy = None
        if evaluated_predictions.exists():
            accurate_count = evaluated_predictions.filter(is_accurate=True).count()
            model_accuracy = round((accurate_count / evaluated_predictions.count()) * 100, 1)

        at_risk_students = registered_students.filter(current_grade__in=['D', 'F']).count()
        grade_distribution = (
            registered_students.exclude(current_grade__isnull=True)
            .values('current_grade')
            .annotate(count=Count('id'))
            .order_by('current_grade')
        )
        grade_labels = [item['current_grade'] for item in grade_distribution]
        grade_data = [item['count'] for item in grade_distribution]
        recent_predictions = Prediction.objects.select_related('student').order_by('-created_at')[:5]
        avg_predicted_score = Prediction.objects.aggregate(avg_score=Avg('predicted_score'))['avg_score']

        context.update({
            'total_students': total_students,
            'total_predictions': total_predictions,
            'model_accuracy': model_accuracy,
            'avg_predicted_score': round(avg_predicted_score, 1) if avg_predicted_score is not None else None,
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
            ensure_student_profile_for_user(user)
            student_profile = Student.objects.get(user=user)
            student_predictions = Prediction.objects.filter(student=student_profile)[:5]
        except Student.DoesNotExist:
            pass

        latest_prediction = student_predictions[0] if student_predictions else None
        latest_recommendation = ''
        if latest_prediction:
            recs = performance_model.generate_recommendations(latest_prediction.input_features)
            latest_recommendation = recs[0]['message'] if recs else ''

        context.update({
            'student_profile': student_profile,
            'student_predictions': student_predictions,
            'latest_prediction': latest_prediction,
            'latest_recommendation': latest_recommendation,
        })

    return render(request, 'dashboard.html', context)
