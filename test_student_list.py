#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'performance_system.settings')
django.setup()

from apps.students.models import Student
from apps.predictions.models import Prediction

def test_student_list():
    print("=== Student Performance System Test ===")

    # Check total counts
    total_students = Student.objects.count()
    total_predictions = Prediction.objects.count()

    print(f"Total students: {total_students}")
    print(f"Total predictions: {total_predictions}")

    if total_students > 0:
        # Get first student with predictions
        student = Student.objects.prefetch_related('predictions').first()
        print(f"\nSample student: {student.get_full_name()}")
        print(f"Student ID: {student.student_id}")
        print(f"Email: {student.email}")
        print(f"Attendance: {student.attendance_percentage}%")
        print(f"Study time: {student.study_time} hours")
        print(f"Previous grade: {student.previous_grade}")
        print(f"Predictions count: {student.predictions.count()}")

        if student.predictions.exists():
            latest_pred = student.predictions.order_by('-created_at').first()
            print(f"Latest prediction: Grade {latest_pred.predicted_grade}, Score {latest_pred.predicted_score:.1f}")
            print(f"Confidence: {latest_pred.confidence:.2f}")
        else:
            print("No predictions for this student yet")

    print("\n=== Test completed successfully ===")

if __name__ == '__main__':
    test_student_list()