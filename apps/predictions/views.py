# apps/predictions/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db.models import Count, Avg
from apps.students.models import Student
from apps.predictions.models import Prediction
from apps.predictions.forms import PredictionForm
from apps.predictions.ml_model import performance_model
import json

@login_required
def predict_student(request, student_id=None):
    """Make prediction for a student"""
    if not (request.user.is_superuser or getattr(request.user, 'role', None) in ['admin', 'teacher']):
        raise PermissionDenied

    if student_id:
        student = get_object_or_404(Student, id=student_id)
    else:
        student = None
    
    if request.method == 'POST':
        form = PredictionForm(request.POST, initial={'student': student})
        if form.is_valid():
            # Get features from form
            features = {
                'attendance_percentage': form.cleaned_data['attendance_percentage'],
                'previous_grade': form.cleaned_data['previous_grade'],
                'study_time': form.cleaned_data['study_time'],
                'failures_past': form.cleaned_data['failures_past'],
                'family_support': form.cleaned_data['family_support'],
                'extracurricular_activities': form.cleaned_data['extracurricular_activities'],
                'internet_access': form.cleaned_data['internet_access'],
                'parent_education': form.cleaned_data['parent_education'],
            }
            
            # Make prediction
            if not performance_model.is_model_trained():
                messages.warning(request, 'Model not trained yet. Training now...')
                performance_model.train_model()
            
            try:
                prediction_result = performance_model.predict(features)
                
                # Save prediction to database
                prediction = Prediction(
                    student=form.cleaned_data['student'],
                    predicted_by=request.user,
                    **features,
                    predicted_grade=prediction_result['predicted_grade'],
                    predicted_score=prediction_result['confidence'],
                    confidence_score=prediction_result['confidence'],
                    feature_importance=performance_model.get_feature_importance()
                )
                prediction.save()
                
                # Prepare context for result page
                # Format feature names for display (e.g., 'study_time' -> 'Study Time')
                raw_importance = performance_model.get_feature_importance()
                display_importance = {k.replace('_', ' ').title(): v for k, v in raw_importance.items()}

                context = {
                    'prediction': prediction,
                    'prediction_result': prediction_result,
                    'feature_importance': display_importance,
                    'student': form.cleaned_data['student'],
                }
                
                messages.success(request, f'Prediction completed! Student will likely get grade: {prediction_result["predicted_grade"]}')
                return render(request, 'predictions/result.html', context)
                
            except Exception as e:
                messages.error(request, f'Error making prediction: {str(e)}')
    else:
        form = PredictionForm(initial={'student': student} if student else {})
    
    context = {
        'form': form,
        'student': student,
        'students': Student.objects.all(),
    }
    return render(request, 'predictions/predict.html', context)

@login_required
def prediction_history(request):
    """View prediction history"""
    if request.user.is_superuser or getattr(request.user, 'role', None) in ['admin', 'teacher']:
        predictions = Prediction.objects.all()
    else:  # student
        try:
            student = Student.objects.get(user=request.user)
            predictions = Prediction.objects.filter(student=student)
        except Student.DoesNotExist:
            predictions = Prediction.objects.none()
    
    context = {
        'predictions': predictions,
        'total_predictions': predictions.count(),
    }
    return render(request, 'predictions/history.html', context)

@login_required
def retrain_model(request):
    """Retrain the ML model with current data"""
    if not (request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'):
        raise PermissionDenied

    if request.method == 'POST':
        # Get all students with final scores
        students = Student.objects.exclude(final_score__isnull=True)
        
        if students.count() < 10:
            messages.error(request, f'Need at least 10 students with grades to retrain model. Currently have {students.count()}.')
            return redirect('predictions:model_info')
        
        # Prepare training data
        import pandas as pd
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
        
        # Train model
        accuracy, importance = performance_model.train_model(df)
        
        messages.success(request, f'Model retrained successfully! Accuracy: {accuracy:.2%}')
        
    return redirect('predictions:model_info')

@login_required
def model_info(request):
    """Display model information and metrics"""
    is_trained = performance_model.is_model_trained()
    feature_importance = None
    
    if is_trained:
        performance_model.load_model()
        raw_importance = performance_model.get_feature_importance()
        feature_importance = {k.replace('_', ' ').title(): v for k, v in raw_importance.items()}
    
    # Get statistics
    total_predictions = Prediction.objects.count()
    avg_confidence = Prediction.objects.aggregate(Avg('confidence_score'))['confidence_score__avg']
    
    context = {
        'is_trained': is_trained,
        'feature_importance': feature_importance,
        'total_predictions': total_predictions,
        'avg_confidence': avg_confidence,
        'total_students': Student.objects.count(),
        'students_with_grades': Student.objects.exclude(final_score__isnull=True).count(),
    }
    return render(request, 'predictions/model_info.html', context)