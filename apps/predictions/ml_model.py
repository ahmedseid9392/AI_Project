# apps/predictions/ml_model.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
from sklearn.utils.multiclass import type_of_target
import joblib
import os
import json
from django.conf import settings


class StudentPerformanceModel:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}  # For categorical features
        self.feature_names = []
        self.target_column = None
        self.feature_stats = {}
        self.model_dir = os.path.join(settings.BASE_DIR, 'models')
        self.model_path = os.path.join(self.model_dir, 'student_performance_model.pkl')
        self.scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
        self.config_path = os.path.join(self.model_dir, 'model_config.json')
        self.encoders_path = os.path.join(self.model_dir, 'label_encoders.pkl')

    def _save_config(self, feature_names, target_column, column_types, feature_stats=None):
        """Save model configuration to disk."""
        os.makedirs(self.model_dir, exist_ok=True)
        config = {
            'feature_names': feature_names,
            'target_column': target_column,
            'column_types': column_types,
            'feature_stats': feature_stats or {},
        }
        with open(self.config_path, 'w') as f:
            json.dump(config, f)

    def _load_config(self):
        """Load model configuration from disk."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            self.feature_names = config.get('feature_names', [])
            self.target_column = config.get('target_column', None)
            self.feature_stats = config.get('feature_stats', {})
            return config
        return None

    def _detect_column_types(self, df, exclude_columns=None):
        """Auto-detect column types from a DataFrame."""
        exclude = set(exclude_columns or [])
        column_types = {}
        for col in df.columns:
            if col in exclude:
                continue
            if df[col].dtype in ['bool']:
                column_types[col] = 'boolean'
            elif df[col].dtype in ['int64', 'float64', 'int32', 'float32']:
                # Check if it's really boolean (0/1 only)
                unique_vals = df[col].dropna().unique()
                if set(unique_vals).issubset({0, 1, 0.0, 1.0, True, False}):
                    column_types[col] = 'boolean'
                else:
                    column_types[col] = 'numeric'
            elif df[col].dtype == 'object':
                unique_vals = df[col].dropna().unique()
                if len(unique_vals) <= 20:
                    column_types[col] = 'categorical'
                else:
                    column_types[col] = 'text'
            else:
                column_types[col] = 'numeric'
        return column_types

    def _prepare_features(self, df, feature_names, column_types, fit=False):
        """Prepare features for the model — encode categoricals, convert booleans."""
        df_prepared = pd.DataFrame()

        for col in feature_names:
            if col not in df.columns:
                raise ValueError(f"Missing feature column: {col}")

            col_type = column_types.get(col, 'numeric')

            if col_type == 'boolean':
                df_prepared[col] = df[col].astype(int)
            elif col_type == 'categorical':
                if fit:
                    le = LabelEncoder()
                    df_prepared[col] = le.fit_transform(df[col].astype(str))
                    self.label_encoders[col] = le
                else:
                    le = self.label_encoders.get(col)
                    if le:
                        # Handle unseen labels gracefully
                        df_prepared[col] = df[col].astype(str).map(
                            lambda x: le.transform([x])[0] if x in le.classes_ else -1
                        )
                    else:
                        df_prepared[col] = 0
            else:
                df_prepared[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df_prepared

    def train_model(self, data=None, feature_names=None, target_column=None, column_types=None):
        """Train the model dynamically based on the uploaded data columns."""

        if data is None:
            data = self._generate_sample_data()
            feature_names = [c for c in data.columns if c != 'grade']
            target_column = 'grade'

        if target_column is None:
            target_column = 'grade'

        if feature_names is None:
            feature_names = [c for c in data.columns if c != target_column]

        # Auto-detect column types if not provided
        if column_types is None:
            column_types = self._detect_column_types(data, exclude_columns=[target_column])

        # Filter to only usable columns (numeric, boolean, categorical)
        usable_features = [
            col for col in feature_names
            if column_types.get(col) in ('numeric', 'boolean', 'categorical')
        ]

        self.feature_names = usable_features
        self.target_column = target_column

        # Prepare features
        X = self._prepare_features(data, usable_features, column_types, fit=True)
        y = data[target_column]

        # Auto-convert continuous targets to grades (A, B, C, D, F) since we are using a Classifier
        if type_of_target(y.dropna()) == 'continuous':
            try:
                # Bin into 5 equal-sized buckets
                y = pd.qcut(y, q=5, labels=['F', 'D', 'C', 'B', 'A'], duplicates='drop')
            except ValueError:
                # Fallback to equal-width buckets if qcut fails due to low variance
                y = pd.cut(y, bins=5, labels=['F', 'D', 'C', 'B', 'A'])
            y = y.astype(str)

        # Drop rows with NaN target
        mask = y.notna()
        X = X[mask]
        y = y[mask]

        if len(X) < 5:
            raise ValueError(f"Not enough valid data rows to train (got {len(X)}, need at least 5)")

        # Split data
        stratify_y = y
        if y.value_counts().min() < 2:
            stratify_y = None

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=stratify_y
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        self.model.fit(X_train_scaled, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)

        print(f"Model trained with accuracy: {accuracy:.2%}")
        print(f"Features used: {usable_features}")
        print(f"Target column: {target_column}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))

        # Feature importance
        importance_dict = dict(zip(usable_features, self.model.feature_importances_))

        # Calculate feature statistics for dynamic recommendations
        feature_stats = {}
        for col in usable_features:
            if column_types.get(col) == 'numeric':
                feature_stats[col] = {
                    'min': float(X[col].min()),
                    'max': float(X[col].max()),
                    'mean': float(X[col].mean()),
                    'median': float(X[col].median()),
                }

        # Save everything
        self._save_config(usable_features, target_column, column_types, feature_stats)
        self.save_model()

        return accuracy, importance_dict

    def predict(self, features):
        """Predict using dynamically loaded features."""
        if self.model is None:
            self.load_model()

        config = self._load_config()
        if config is None:
            raise ValueError("No model configuration found. Please train the model first.")

        feature_names = config['feature_names']
        column_types = config.get('column_types', {})

        # Convert features dict to DataFrame
        if isinstance(features, dict):
            features_df = pd.DataFrame([features])
        else:
            features_df = features

        # Prepare features
        X = self._prepare_features(features_df, feature_names, column_types, fit=False)

        # Scale
        features_scaled = self.scaler.transform(X)

        # Predict
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]
        confidence = max(probabilities) * 100

        return {
            'predicted_grade': str(prediction),
            'confidence': confidence,
            'probabilities': {str(k): float(v) for k, v in zip(self.model.classes_, probabilities)}
        }

    def get_feature_importance(self):
        """Get feature importance from trained model."""
        if self.model is None:
            self.load_model()

        if not self.feature_names:
            config = self._load_config()
            if config:
                self.feature_names = config['feature_names']

        importance_dict = dict(zip(self.feature_names, self.model.feature_importances_))
        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

    def get_feature_names(self):
        """Get the list of feature names from config."""
        if not self.feature_names:
            config = self._load_config()
            if config:
                self.feature_names = config['feature_names']
        return self.feature_names

    def get_column_types(self):
        """Get column types from config."""
        config = self._load_config()
        if config:
            return config.get('column_types', {})
        return {}

    def get_feature_stats(self):
        """Get feature statistics from config."""
        if not hasattr(self, 'feature_stats') or not self.feature_stats:
            config = self._load_config()
            if config:
                self.feature_stats = config.get('feature_stats', {})
        return getattr(self, 'feature_stats', {})

    def save_model(self):
        """Save model to disk."""
        os.makedirs(self.model_dir, exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
        joblib.dump(self.label_encoders, self.encoders_path)

    def load_model(self):
        """Load model from disk."""
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            if os.path.exists(self.encoders_path):
                self.label_encoders = joblib.load(self.encoders_path)
            self._load_config()
            return True
        return False

    def is_model_trained(self):
        """Check if model exists."""
        return os.path.exists(self.model_path)

    def _generate_sample_data(self, n_samples=1000):
        """Generate synthetic sample data for training."""
        np.random.seed(42)

        data = {
            'attendance': np.random.uniform(40, 100, n_samples),
            'previous_grade': np.random.uniform(30, 100, n_samples),
            'study_hours': np.random.uniform(0, 40, n_samples),
            'failures_past': np.random.randint(0, 4, n_samples),
            'family_support': np.random.randint(1, 11, n_samples),
            'extra_activities': np.random.choice([0, 1], n_samples),
            'internet_access': np.random.choice([0, 1], n_samples),
            'parent_education': np.random.randint(1, 11, n_samples),
        }

        df = pd.DataFrame(data)

        score = (
            df['attendance'] * 0.3 +
            df['previous_grade'] * 0.3 +
            df['study_hours'] * 0.15 +
            (10 - df['failures_past'] * 2) +
            df['family_support'] * 0.5 +
            df['extra_activities'] * 5 +
            df['internet_access'] * 3 +
            df['parent_education'] * 0.5
        )
        score += np.random.normal(0, 5, n_samples)

        def score_to_grade(s):
            if s >= 85: return 'A'
            elif s >= 70: return 'B'
            elif s >= 55: return 'C'
            elif s >= 40: return 'D'
            else: return 'F'

        df['grade'] = [score_to_grade(s) for s in score]
        return df


# Global instance
performance_model = StudentPerformanceModel()