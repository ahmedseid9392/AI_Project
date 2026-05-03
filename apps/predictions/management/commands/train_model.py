# apps/predictions/management/commands/train_model.py
from django.core.management.base import BaseCommand
from apps.predictions.ml_model import performance_model
from apps.students.models import Student
import pandas as pd

class Command(BaseCommand):
    help = 'Train the student performance prediction model'
    
    def handle(self, *args, **options):
        self.stdout.write('Training model...')
        
        # Check if we have real data
        students = Student.objects.exclude(final_score__isnull=True)
        
        if students.count() >= 10:
            self.stdout.write(f'Using {students.count()} real student records...')
            data = []
            for student in students:
                data.append({
                    'attendance_percentage': student.attendance_percentage,
                    'previous_grade': student.previous_grade,
                    'study_time': student.study_time,
                    'failures_past': student.failures_past,
                    'family_support': student.family_support,
                    'extracurricular_activities': int(student.extracurricular_activities),
                    'internet_access': int(student.internet_access_at_home),
                    'parent_education': student.parent_education_level,
                    'grade': student.current_grade,
                })
            df = pd.DataFrame(data)
        else:
            self.stdout.write('Using synthetic data for training...')
            df = None
        
        accuracy, importance = performance_model.train_model(df)
        self.stdout.write(self.style.SUCCESS(f'Model trained successfully! Accuracy: {accuracy:.2%}'))
        
        self.stdout.write('\nFeature Importance:')
        for feature, imp in importance.items():
            self.stdout.write(f'{feature}: {imp:.3f}')