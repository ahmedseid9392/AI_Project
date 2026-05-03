# apps/students/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Student(models.Model):
    GRADE_CHOICES = (
        ('A', 'A (Excellent)'),
        ('B', 'B (Good)'),
        ('C', 'C (Average)'),
        ('D', 'D (Below Average)'),
        ('F', 'F (Fail)'),
    )
    
    # Basic Information
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    student_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    
    # Academic Data
    attendance_percentage = models.FloatField(help_text="Attendance percentage (0-100)")
    previous_grade = models.FloatField(help_text="Previous year grade (0-100)")
    study_time = models.FloatField(help_text="Average study hours per week")
    failures_past = models.IntegerField(help_text="Number of past failures")
    
    # Behavioral Data
    family_support = models.IntegerField(help_text="Family support level (1-10)")
    extracurricular_activities = models.BooleanField(default=False)
    internet_access_at_home = models.BooleanField(default=True)
    parent_education_level = models.IntegerField(help_text="Parent education (1-10)", default=5)
    
    # Performance
    current_grade = models.CharField(max_length=1, choices=GRADE_CHOICES, blank=True, null=True)
    final_score = models.FloatField(blank=True, null=True, help_text="Final exam score (0-100)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_id})"
    
    def calculate_performance_label(self):
        """Convert final score to grade"""
        if self.final_score is None:
            return None
        if self.final_score >= 85:
            return 'A'
        elif self.final_score >= 70:
            return 'B'
        elif self.final_score >= 55:
            return 'C'
        elif self.final_score >= 40:
            return 'D'
        else:
            return 'F'
    
    def save(self, *args, **kwargs):
        if self.final_score:
            self.current_grade = self.calculate_performance_label()
        super().save(*args, **kwargs)