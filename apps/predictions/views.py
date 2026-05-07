# apps/predictions/views.py
import json
import pandas as pd

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db.models import Avg

from apps.students.models import Student
from apps.students.utils import registered_student_queryset
from apps.predictions.models import Prediction, DatasetConfig
from apps.predictions.forms import EXCLUDED_INPUT_FIELDS, build_dynamic_prediction_form, TargetColumnForm
from apps.predictions.ml_model import performance_model


def _populate_hidden_prediction_features(features, user, student_obj=None):
    populated_features = dict(features)
    feature_names = performance_model.get_feature_names()

    for feature_name in feature_names:
        lower_name = feature_name.lower()
        if lower_name not in EXCLUDED_INPUT_FIELDS or feature_name in populated_features:
            continue

        if lower_name == 'student_id':
            populated_features[feature_name] = student_obj.student_id if student_obj else user.username
        elif lower_name in {'name', 'full_name', 'student_name'}:
            if student_obj:
                populated_features[feature_name] = student_obj.get_full_name()
            else:
                populated_features[feature_name] = user.get_full_name() or user.username
        else:
            populated_features[feature_name] = ''

    return populated_features


@login_required
def predict_student(request):
    """Make a prediction using the dynamically trained model."""
    user = request.user
    is_staff = user.is_superuser or getattr(user, 'role', None) in ['admin', 'teacher']

    # Check if model is trained
    if not performance_model.is_model_trained():
        messages.warning(request, 'No model trained yet. An admin must upload a dataset and train the model first.')
        return redirect('dashboard')

    # Load model to get features
    performance_model.load_model()
    DynamicForm = build_dynamic_prediction_form(is_staff=is_staff)

    if request.method == 'POST':
        form = DynamicForm(request.POST)
        if form.is_valid():
            features = form.cleaned_data

            # Extract student if staff, then remove from features dictionary
            student_obj = None
            if is_staff and 'student' in features:
                student_obj = features.pop('student')
            elif not is_staff:
                try:
                    student_obj = Student.objects.get(user=user)
                except Student.DoesNotExist:
                    pass

            try:
                features = _populate_hidden_prediction_features(features, user, student_obj)
                prediction_result = performance_model.predict(features)

                # Save prediction
                prediction = Prediction(
                    student=student_obj,
                    predicted_by=user,
                    input_features=features,
                    predicted_grade=prediction_result['predicted_grade'],
                    predicted_score=prediction_result['predicted_score'],
                    confidence_score=prediction_result['confidence'],
                    feature_importance=performance_model.get_feature_importance()
                )
                prediction.save()

                # Format feature importance for display
                raw_importance = performance_model.get_feature_importance()
                display_importance = {k.replace('_', ' ').title(): v * 100 for k, v in raw_importance.items()}

                feature_comparisons = []
                recommendation_messages = performance_model.generate_recommendations(features)
                feature_stats = performance_model.get_feature_stats()

                for feat_name, user_val in features.items():
                    if feat_name in feature_stats:
                        stats = feature_stats[feat_name]
                        mean_val = stats.get('mean', 0)
                        display_name = feat_name.replace('_', ' ').title()

                        if isinstance(user_val, (int, float)):
                            if user_val > mean_val * 1.1:
                                status = 'high'
                                msg = f"Higher than average ({user_val} vs avg {mean_val:.1f})"
                            elif user_val < mean_val * 0.9:
                                status = 'low'
                                msg = f"Lower than average ({user_val} vs avg {mean_val:.1f})"
                            else:
                                status = 'average'
                                msg = f"Average ({user_val})"
                        else:
                            status = 'average'
                            msg = f"{user_val}"

                        feature_comparisons.append({
                            'name': display_name,
                            'status': status,
                            'message': msg
                        })

                context = {
                    'prediction': prediction,
                    'prediction_result': prediction_result,
                    'feature_importance': display_importance,
                    'input_features': {k.replace('_', ' ').title(): v for k, v in features.items()},
                    'feature_comparisons': feature_comparisons,
                    'recommendation_messages': recommendation_messages,
                }

                messages.success(request, f'Prediction completed! Predicted grade: {prediction_result["predicted_grade"]}')
                return render(request, 'predictions/result.html', context)

            except Exception as e:
                messages.error(request, f'Error making prediction: {str(e)}')
    else:
        form = DynamicForm()

    context = {
        'form': form,
        'is_staff': is_staff,
    }
    return render(request, 'predictions/predict.html', context)


@login_required
def prediction_history(request):
    """View prediction history — filtered by role."""
    if request.user.is_superuser or getattr(request.user, 'role', None) in ['admin', 'teacher']:
        predictions = Prediction.objects.all()
    else:
        try:
            student = Student.objects.get(user=request.user)
            predictions = Prediction.objects.filter(student=student)
        except Student.DoesNotExist:
            # Also show predictions made by this user even without student profile
            predictions = Prediction.objects.filter(predicted_by=request.user)

    history_entries = []
    for prediction in predictions:
        recs = performance_model.generate_recommendations(prediction.input_features)
        recommendation_summary = recs[0]['message'] if recs else ''
        display_name = prediction.input_features.get('student_name')
        if not display_name and prediction.student:
            display_name = prediction.student.get_full_name() or f'{prediction.student.first_name} {prediction.student.last_name}'
        history_entries.append({
            'prediction': prediction,
            'display_name': display_name or 'Not linked',
            'recommendation_summary': recommendation_summary,
        })

    context = {
        'history_entries': history_entries,
        'total_predictions': predictions.count(),
    }
    return render(request, 'predictions/history.html', context)


@login_required
def delete_prediction(request, pk):
    prediction = get_object_or_404(Prediction, pk=pk)
    user = request.user
    allowed = user.is_superuser or getattr(user, 'role', None) in ['admin', 'teacher']
    if not allowed:
        raise PermissionDenied

    if request.method == 'POST':
        prediction.delete()
        messages.success(request, 'Prediction deleted successfully.')
    return redirect('predictions:history')


@login_required
def upload_dataset(request):
    """Admin: Step 1 — upload CSV, Step 2 — select target column, then train."""
    if not (request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'):
        raise PermissionDenied

    # Step 2: target column selection (CSV already in session)
    if request.method == 'POST' and 'target_column' in request.POST:
        csv_path = request.session.get('uploaded_csv_path')
        if not csv_path:
            messages.error(request, 'Session expired. Please upload the file again.')
            return redirect('predictions:upload_dataset')

        try:
            import os
            df = pd.read_csv(csv_path)
            columns = list(df.columns)

            form = TargetColumnForm(columns, request.POST)
            if form.is_valid():
                target_col = form.cleaned_data['target_column']
                exclude_cols = form.cleaned_data.get('exclude_columns', [])

                # Feature columns = all columns minus target and excluded
                feature_cols = [c for c in columns if c != target_col and c not in exclude_cols]

                # Detect column types
                column_types = performance_model._detect_column_types(df, exclude_columns=[target_col] + exclude_cols)

                # Train the model
                accuracy, importance = performance_model.train_model(
                    data=df,
                    feature_names=feature_cols,
                    target_column=target_col,
                    column_types=column_types
                )

                # Save config to database
                DatasetConfig.objects.all().delete()  # Keep only one active config
                DatasetConfig.objects.create(
                    name='uploaded_dataset',
                    feature_columns=feature_cols,
                    target_column=target_col,
                    column_types=column_types,
                    all_columns=columns,
                    num_records=len(df),
                    uploaded_by=request.user,
                )

                # Import student records from the dataset into the Student database table
                imported_count = 0
                for index, row in df.iterrows():
                    try:
                        # Use student_id from CSV if exists, otherwise generate one
                        s_id = str(row.get('student_id', row.get('id', f'STU-{1000 + index}')))
                        
                        # Handle name parsing (Full Name vs First/Last columns)
                        csv_name = str(row.get('name', row.get('full_name', '')))
                        f_name = str(row.get('first_name', ''))
                        l_name = str(row.get('last_name', ''))
                        
                        if csv_name and not (f_name or l_name):
                            parts = csv_name.split(' ', 1)
                            f_name = parts[0]
                            l_name = parts[1] if len(parts) > 1 else 'Student'

                        # Map dataset columns to Student model fields with sensible defaults
                        student_data = {
                            'first_name': f_name or str(row.get('first_name', 'Student')),
                            'last_name': l_name or str(row.get('last_name', f'User_{index}')),
                            'email': str(row.get('email', f'student_{index}@example.com')),
                            'attendance_percentage': float(row.get('attendance', row.get('attendance_percentage', 0))),
                            'previous_grade': float(row.get('previous_grade', row.get('prev_grade', 0))),
                            'study_time': float(row.get('study_time', row.get('study_hours', 0))),
                            'failures_past': int(row.get('failures', row.get('failures_past', 0))),
                            'family_support': int(row.get('family_support', 0)),
                            'parent_education_level': int(row.get('parent_education', 0)),
                        }

                        # Logic for boolean fields that might be strings like 'yes'/'no' in CSV
                        for field in ['internet_access_at_home', 'extracurricular_activities']:
                            val = row.get(field, row.get(field.split('_')[0], None))
                            if val is not None:
                                if isinstance(val, str):
                                    student_data[field] = val.lower() in ('yes', 'true', '1', 'y')
                                else:
                                    student_data[field] = bool(val)

                        # Map the target column (the grade/score from CSV) to Student record
                        try:
                            target_val = row.get(target_col)
                            student_data['final_score'] = float(target_val)
                            # Automatically assign a grade label based on score for the list view
                            if student_data['final_score'] >= 85: student_data['current_grade'] = 'A'
                            elif student_data['final_score'] >= 70: student_data['current_grade'] = 'B'
                            elif student_data['final_score'] >= 55: student_data['current_grade'] = 'C'
                            elif student_data['final_score'] >= 40: student_data['current_grade'] = 'D'
                            else: student_data['current_grade'] = 'F'
                        except (ValueError, TypeError):
                            # If target is already a letter grade
                            if isinstance(target_val, str) and target_val.strip().upper() in ['A', 'B', 'C', 'D', 'F']:
                                student_data['current_grade'] = target_val.strip().upper()

                        Student.objects.update_or_create(student_id=s_id, defaults=student_data)
                        imported_count += 1
                    except Exception:
                        continue # Skip rows that have incompatible data types

                # Clean up
                if os.path.exists(csv_path):
                    os.remove(csv_path)
                if 'uploaded_csv_path' in request.session:
                    del request.session['uploaded_csv_path']

                messages.success(
                    request,
                    f'Model trained (Accuracy: {accuracy:.2%}) and {imported_count} students '
                    f'have been imported/updated in the system records.'
                )
                return redirect('predictions:model_info')
            else:
                return render(request, 'predictions/select_target.html', {
                    'form': form,
                    'columns': columns,
                    'preview_rows': df.head(5).to_html(classes='table table-sm table-striped', index=False),
                })

        except Exception as e:
            messages.error(request, f'Error processing dataset: {str(e)}')
            return redirect('predictions:upload_dataset')

    # Step 1: Upload CSV
    if request.method == 'POST' and request.FILES.get('dataset'):
        csv_file = request.FILES['dataset']

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('predictions:upload_dataset')

        try:
            # Save uploaded file temporarily
            import os
            upload_dir = os.path.join(settings.BASE_DIR, 'models', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            temp_path = os.path.join(upload_dir, 'temp_dataset.csv')

            with open(temp_path, 'wb+') as f:
                for chunk in csv_file.chunks():
                    f.write(chunk)

            df = pd.read_csv(temp_path)
            columns = list(df.columns)

            # Store path in session for step 2
            request.session['uploaded_csv_path'] = temp_path

            # Show column selection form
            form = TargetColumnForm(columns)

            return render(request, 'predictions/select_target.html', {
                'form': form,
                'columns': columns,
                'num_rows': len(df),
                'num_cols': len(columns),
                'preview_rows': df.head(5).to_html(classes='table table-sm table-striped', index=False),
            })

        except Exception as e:
            messages.error(request, f'Error reading CSV: {str(e)}')
            return redirect('predictions:upload_dataset')

    return render(request, 'predictions/upload_dataset.html')


@login_required
def retrain_model(request):
    """Retrain the model using the stored dataset config."""
    if not (request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'):
        raise PermissionDenied

    if request.method == 'POST':
        messages.info(request, 'To retrain, please upload a new dataset.')
    return redirect('predictions:upload_dataset')


@login_required
def model_info(request):
    """Display model information and metrics."""
    is_trained = performance_model.is_model_trained()
    feature_importance = None
    feature_names = []
    dataset_config = DatasetConfig.get_active()
    registered_students = registered_student_queryset()

    if is_trained:
        performance_model.load_model()
        raw_importance = performance_model.get_feature_importance()
        feature_importance = {k.replace('_', ' ').title(): v * 100 for k, v in raw_importance.items()}
        feature_names = performance_model.get_feature_names()

    total_predictions = Prediction.objects.count()
    avg_confidence = Prediction.objects.aggregate(Avg('confidence_score'))['confidence_score__avg']
    students_with_grades = registered_students.exclude(final_score__isnull=True).count()

    context = {
        'is_trained': is_trained,
        'feature_importance': feature_importance,
        'feature_names': feature_names,
        'total_predictions': total_predictions,
        'avg_confidence': avg_confidence,
        'total_students': registered_students.count(),
        'students_with_grades': students_with_grades,
        'dataset_config': dataset_config,
    }
    return render(request, 'predictions/model_info.html', context)


# Need settings for BASE_DIR
from django.conf import settings
