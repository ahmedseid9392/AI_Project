from django import forms
from apps.predictions.ml_model import performance_model
from apps.students.models import Student


def build_dynamic_prediction_form(feature_names=None, column_types=None, is_staff=False):
    """Dynamically create a prediction form based on the trained model's features."""

    if feature_names is None:
        feature_names = performance_model.get_feature_names()
    if column_types is None:
        column_types = performance_model.get_column_types()

    # Always require a name field at the top of the form, independent of the ML model
    fields = {
        'student_name': forms.CharField(
            label="Full Name",
            required=True,
            widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your full name'})
        )
    }

    for col in feature_names:
        col_type = column_types.get(col, 'numeric')
        label = col.replace('_', ' ').title()

        if col_type == 'boolean':
            # For booleans like internet_access or extra_activities, use a Yes/No dropdown for better UI
            fields[col] = forms.ChoiceField(
                choices=[(1, 'Yes'), (0, 'No')],
                label=label,
                widget=forms.Select(attrs={'class': 'form-select'})
            )
        elif col_type == 'categorical':
            # We'll allow free text input for categorical (or could load choices from encoder)
            le = performance_model.label_encoders.get(col)
            if le and hasattr(le, 'classes_'):
                choices = [('', '-- Select --')] + [(c, c) for c in le.classes_]
                fields[col] = forms.ChoiceField(
                    choices=choices,
                    label=label,
                    widget=forms.Select(attrs={'class': 'form-select'})
                )
            else:
                fields[col] = forms.CharField(
                    label=label,
                    widget=forms.TextInput(attrs={'class': 'form-control'})
                )
        else:
            # Smart heuristics for numeric fields based on column names
            attrs = {'class': 'form-control', 'step': 'any'}
            min_val = None
            max_val = None
            
            lower_col = col.lower()
            if 'age' in lower_col:
                min_val = 0
                attrs['step'] = '1'
            elif 'attendance' in lower_col or 'score' in lower_col or 'grade' in lower_col or 'percent' in lower_col:
                min_val = 0
                max_val = 100
            elif 'hour' in lower_col or 'time' in lower_col or 'past' in lower_col or 'failures' in lower_col:
                min_val = 0
                
            if min_val is not None:
                attrs['min'] = min_val
            if max_val is not None:
                attrs['max'] = max_val

            fields[col] = forms.FloatField(
                label=label,
                min_value=min_val,
                max_value=max_val,
                widget=forms.NumberInput(attrs=attrs)
            )

    if is_staff:
        fields['student'] = forms.ModelChoiceField(
            queryset=Student.objects.all(),
            required=False,
            label="Select Student (Optional)",
            widget=forms.Select(attrs={'class': 'form-select'}),
            help_text="If you want to save this prediction to a specific student's profile, select them here."
        )

    # Create the form class dynamically
    DynamicForm = type('DynamicPredictionForm', (forms.Form,), fields)
    return DynamicForm


class DatasetUploadForm(forms.Form):
    """Form for uploading a CSV dataset."""
    dataset = forms.FileField(
        label='CSV File',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv'}),
        help_text='Upload a CSV file with your student data.'
    )


class TargetColumnForm(forms.Form):
    """Form for selecting which column is the target (grade to predict)."""
    target_column = forms.ChoiceField(
        label='Target Column (what to predict)',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Select the column that contains the grade/label the model should predict.'
    )
    exclude_columns = forms.MultipleChoiceField(
        label='Columns to Exclude (optional)',
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        help_text='Select any columns that should NOT be used as features (e.g. student_id, name).'
    )

    def __init__(self, columns=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if columns:
            col_choices = [(c, c) for c in columns]
            self.fields['target_column'].choices = col_choices
            self.fields['exclude_columns'].choices = col_choices
