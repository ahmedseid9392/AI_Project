# apps/predictions/ml_model.py
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
from django.conf import settings

class StudentPerformanceModel:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = [
            'attendance_percentage', 'previous_grade', 'study_time',
            'failures_past', 'family_support', 'extracurricular_activities',
            'internet_access', 'parent_education'
        ]
        self.model_path = os.path.join(settings.BASE_DIR, 'models', 'student_performance_model.pkl')
        self.scaler_path = os.path.join(settings.BASE_DIR, 'models', 'scaler.pkl')
        
    def generate_sample_data(self, n_samples=1000):
        """Generate synthetic sample data for training"""
        np.random.seed(42)
        
        data = {
            'attendance_percentage': np.random.uniform(40, 100, n_samples),
            'previous_grade': np.random.uniform(30, 100, n_samples),
            'study_time': np.random.uniform(0, 40, n_samples),
            'failures_past': np.random.randint(0, 4, n_samples),
            'family_support': np.random.randint(1, 11, n_samples),
            'extracurricular_activities': np.random.choice([0, 1], n_samples),
            'internet_access': np.random.choice([0, 1], n_samples),
            'parent_education': np.random.randint(1, 11, n_samples),
        }
        
        df = pd.DataFrame(data)
        
        # Generate target variable based on features
        score = (
            df['attendance_percentage'] * 0.3 +
            df['previous_grade'] * 0.3 +
            df['study_time'] * 0.15 +
            (10 - df['failures_past'] * 2) +
            df['family_support'] * 0.5 +
            df['extracurricular_activities'] * 5 +
            df['internet_access'] * 3 +
            df['parent_education'] * 0.5
        )
        
        # Add some noise
        score += np.random.normal(0, 5, n_samples)
        
        # Convert to grade
        def score_to_grade(score):
            if score >= 85:
                return 'A'
            elif score >= 70:
                return 'B'
            elif score >= 55:
                return 'C'
            elif score >= 40:
                return 'D'
            else:
                return 'F'
        
        df['grade'] = df.apply(lambda row: score_to_grade(score[row.name]), axis=1)
        
        return df
    
    def train_model(self, data=None):
        """Train the Random Forest model"""
        if data is None:
            data = self.generate_sample_data()
        
        # Prepare features and target
        X = data[self.feature_names]
        y = data['grade']
        
        # Split data - Stratification requires at least 2 instances of each class.
        # If any class has only 1 member, we must disable stratification to avoid ValueError.
        stratify_y = y
        if not y.empty and y.value_counts().min() < 2:
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
        
        # Evaluate model
        y_pred = self.model.predict(X_test_scaled)
        accuracy = accuracy_score(y_test, y_pred)
        
        print(f"Model trained with accuracy: {accuracy:.2%}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        # Feature importance
        importance_dict = dict(zip(self.feature_names, self.model.feature_importances_))
        print("\nFeature Importance:")
        for feature, importance in sorted(importance_dict.items(), key=lambda x: x[1], reverse=True):
            print(f"{feature}: {importance:.3f}")
        
        # Save model
        self.save_model()
        
        return accuracy, importance_dict
    
    def predict(self, features):
        """Predict student performance"""
        if self.model is None:
            self.load_model()
        
        # Convert features to DataFrame
        if isinstance(features, dict):
            features_df = pd.DataFrame([features])
        else:
            features_df = features
        
        # Ensure all required features are present
        for feature in self.feature_names:
            if feature not in features_df.columns:
                raise ValueError(f"Missing feature: {feature}")
        
        # Scale features
        features_scaled = self.scaler.transform(features_df[self.feature_names])
        
        # Predict
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]
        confidence = max(probabilities) * 100
        
        return {
            'predicted_grade': prediction,
            'confidence': confidence,
            'probabilities': dict(zip(self.model.classes_, probabilities))
        }
    
    def get_feature_importance(self):
        """Get feature importance from trained model"""
        if self.model is None:
            self.load_model()
        
        importance_dict = dict(zip(self.feature_names, self.model.feature_importances_))
        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
    
    def save_model(self):
        """Save model to disk"""
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump(self.model, self.model_path)
        joblib.dump(self.scaler, self.scaler_path)
    
    def load_model(self):
        """Load model from disk"""
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            self.scaler = joblib.load(self.scaler_path)
            return True
        return False
    
    def is_model_trained(self):
        """Check if model exists"""
        return os.path.exists(self.model_path)

# Global instance
performance_model = StudentPerformanceModel()