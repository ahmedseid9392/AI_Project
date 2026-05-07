from django import forms
from django.contrib.auth import get_user_model

from .models import Student

User = get_user_model()


class RegisteredStudentUpdateForm(forms.ModelForm):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = Student
        fields = [
            'student_id',
            'first_name',
            'last_name',
            'attendance_percentage',
            'previous_grade',
            'study_time',
            'failures_past',
            'family_support',
            'extracurricular_activities',
            'internet_access_at_home',
            'parent_education_level',
            'current_grade',
            'final_score',
        ]
        widgets = {
            'student_id': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'attendance_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'previous_grade': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'study_time': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'failures_past': forms.NumberInput(attrs={'class': 'form-control'}),
            'family_support': forms.NumberInput(attrs={'class': 'form-control'}),
            'extracurricular_activities': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'internet_access_at_home': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'parent_education_level': forms.NumberInput(attrs={'class': 'form-control'}),
            'current_grade': forms.Select(attrs={'class': 'form-select'}),
            'final_score': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['username'].initial = self.instance.user.username
            self.fields['email'].initial = self.instance.user.email
        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['email'].widget.attrs['class'] = 'form-control'

    def clean_username(self):
        username = self.cleaned_data['username']
        qs = User.objects.filter(username=username)
        if self.instance.user_id:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError('A user with that username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        qs = User.objects.filter(email=email)
        if self.instance.user_id:
            qs = qs.exclude(pk=self.instance.user_id)
        if email and qs.exists():
            raise forms.ValidationError('A user with that email already exists.')
        return email

    def save(self, commit=True):
        student = super().save(commit=False)
        if student.user:
            student.user.username = self.cleaned_data['username']
            student.user.email = self.cleaned_data['email']
            if commit:
                student.user.save()
        student.email = self.cleaned_data['email']
        if commit:
            student.save()
        return student
