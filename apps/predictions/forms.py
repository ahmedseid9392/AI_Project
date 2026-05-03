from django import forms
from apps.predictions.models import Prediction
from apps.students.models import Student


class PredictionForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=Student.objects.all(),
        label='Student',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Prediction
        fields = [
            'student',
            'attendance_percentage',
            'previous_grade',
            'study_time',
            'failures_past',
            'family_support',
            'extracurricular_activities',
            'internet_access',
            'parent_education',
        ]
        widgets = {
            'attendance_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'previous_grade': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'study_time': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'failures_past': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'family_support': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '10'}),
            'extracurricular_activities': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'internet_access': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'parent_education': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '10'}),
        }
