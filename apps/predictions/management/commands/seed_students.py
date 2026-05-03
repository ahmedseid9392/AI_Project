import random
from django.core.management.base import BaseCommand
from apps.students.models import Student

class Command(BaseCommand):
    help = 'Seed database with sample students for ML testing'

    def handle(self, *args, **options):
        first_names = ['James', 'Mary', 'Robert', 'Patricia', 'John', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']

        self.stdout.write('Seeding sample students...')
        
        count = 0
        # Create 50 students for a more robust dataset and better class distribution
        for i in range(50):
            s_id = f'STU{1000 + i}'
            if not Student.objects.filter(student_id=s_id).exists():
                attendance = random.uniform(60, 100)
                prev_grade = random.uniform(50, 95)
                study = random.uniform(2, 20)
                failures = random.randint(0, 2)
                support = random.randint(1, 10)
                extra = random.choice([True, False])
                internet = random.choice([True, False])
                parent_ed = random.randint(1, 10)
                
                # Heuristic to generate a realistic final score based on features
                score = (attendance * 0.2 + prev_grade * 0.4 + study * 0.5 + (10 - failures * 5)) + random.uniform(-5, 5)
                score = max(min(score, 100), 0) # Clamp between 0-100

                Student.objects.create(
                    student_id=s_id,
                    first_name=random.choice(first_names),
                    last_name=random.choice(last_names),
                    email=f'student{i}@example.com',
                    attendance_percentage=round(attendance, 1),
                    previous_grade=round(prev_grade, 1),
                    study_time=round(study, 1),
                    failures_past=failures,
                    family_support=support,
                    extracurricular_activities=extra,
                    internet_access_at_home=internet,
                    parent_education_level=parent_ed,
                    final_score=round(score, 1) # This triggers current_grade calculation in save()
                )
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully added {count} sample students.'))