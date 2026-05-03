import csv
from django.core.management.base import BaseCommand
from apps.students.models import Student

class Command(BaseCommand):
    help = 'Import student data from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        path = options['csv_path']
        self.stdout.write(f'Importing data from {path}...')
        
        count = 0
        try:
            with open(path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    Student.objects.update_or_create(
                        student_id=row['student_id'],
                        defaults={
                            'first_name': row.get('first_name', 'Imported'),
                            'last_name': row.get('last_name', 'Student'),
                            'attendance_percentage': float(row['attendance_percentage']),
                            'previous_grade': float(row['previous_grade']),
                            'study_time': float(row['study_time']),
                            'failures_past': int(row['failures_past']),
                            'family_support': int(row['family_support']),
                            'extracurricular_activities': row['extracurricular_activities'].lower() == 'true',
                            'internet_access_at_home': row['internet_access_at_home'].lower() == 'true',
                            'parent_education_level': int(row['parent_education_level']),
                            'final_score': float(row['final_score']) if row.get('final_score') else None,
                        }
                    )
                    count += 1
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} students.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing data: {str(e)}'))