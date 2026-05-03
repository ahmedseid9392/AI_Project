# apps/predictions/models.py
from django.db import models
from django.contrib.auth import get_user_model
from apps.students.models import Student

User = get_user_model()


class DatasetConfig(models.Model):
    """Stores metadata about the uploaded dataset so the system adapts dynamically."""
    name = models.CharField(max_length=100, default='default')
    feature_columns = models.JSONField(
        default=list,
        help_text="List of feature column names used for prediction"
    )
    target_column = models.CharField(
        max_length=100,
        help_text="The column name that contains the label/grade to predict"
    )
    column_types = models.JSONField(
        default=dict,
        help_text="Dict mapping column name -> type (numeric, boolean, categorical)"
    )
    all_columns = models.JSONField(
        default=list,
        help_text="All columns in the uploaded CSV"
    )
    num_records = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Dataset '{self.name}' ({len(self.feature_columns)} features, {self.num_records} records)"

    @classmethod
    def get_active(cls):
        """Return the most recent dataset config, or None."""
        return cls.objects.first()


class Prediction(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='predictions', null=True, blank=True)
    predicted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Dynamic input features stored as JSON
    input_features = models.JSONField(default=dict, help_text="All input feature values as key-value pairs")

    # Prediction Results
    predicted_grade = models.CharField(max_length=10)
    predicted_score = models.FloatField(default=0)
    confidence_score = models.FloatField(help_text="Model confidence percentage")

    # Feature Importance at prediction time
    feature_importance = models.JSONField(default=dict)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    is_accurate = models.BooleanField(null=True, blank=True, help_text="Was prediction accurate?")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.student:
            return f"Prediction for {self.student} - {self.predicted_grade}"
        return f"Prediction - {self.predicted_grade} ({self.created_at:%Y-%m-%d})"