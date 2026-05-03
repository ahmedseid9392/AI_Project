# apps/predictions/models.py
from django.db import models
from django.contrib.auth import get_user_model
from apps.students.models import Student

User = get_user_model()

class Prediction(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='predictions')
    predicted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Input Features
    attendance_percentage = models.FloatField()
    previous_grade = models.FloatField()
    study_time = models.FloatField()
    failures_past = models.IntegerField()
    family_support = models.IntegerField()
    extracurricular_activities = models.BooleanField()
    internet_access = models.BooleanField()
    parent_education = models.IntegerField()
    
    # Prediction Results
    predicted_grade = models.CharField(max_length=1)
    predicted_score = models.FloatField()
    confidence_score = models.FloatField(help_text="Model confidence percentage")
    
    # Feature Importance at prediction time
    feature_importance = models.JSONField(default=dict)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    is_accurate = models.BooleanField(null=True, blank=True, help_text="Was prediction accurate?")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Prediction for {self.student} - {self.predicted_grade}"