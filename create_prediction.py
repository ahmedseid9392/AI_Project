#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'performance_system.settings')
django.setup()

from apps.students.models import Student
from apps.predictions.models import Prediction
from apps.predictions.ml_model import StudentPerformanceModel as MLModel

def create_sample_prediction():
    print("=== Creating Sample Prediction ===")

    # Get first student
    student = Student.objects.first()
    if not student:
        print("No students found!")
        return

    print(f"Creating prediction for: {student.get_full_name()}")

    # Create prediction data
    prediction_data = {
        'attendance_percentage': student.attendance_percentage,
        'previous_grade': student.previous_grade,
        'study_time': student.study_time,
        'failures_past': student.failures_past,
        'family_support': student.family_support,
        'extracurricular_activities': student.extracurricular_activities,
        'internet_access': student.internet_access_at_home,
        'parent_education': student.parent_education_level,
    }

    # Load model and make prediction
    model = MLModel()
    if not model.is_model_trained():
        print("Model not trained!")
        return

    result = model.predict(prediction_data)
    recommendations = model.generate_recommendations(prediction_data, result['grade'])

    # Save prediction
    prediction = Prediction.objects.create(
        student=student,
        predicted_grade=result['grade'],
        predicted_score=result['score'],
        confidence=result['confidence'],
        features_used=prediction_data,
        recommendations=recommendations
    )

    print(f"Prediction created: Grade {prediction.predicted_grade}, Score {prediction.predicted_score:.1f}")
    print(f"Confidence: {prediction.confidence:.2f}")
    print(f"Recommendations: {len(recommendations)} items")

if __name__ == '__main__':
    create_sample_prediction()