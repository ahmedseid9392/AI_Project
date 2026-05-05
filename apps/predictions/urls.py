from django.urls import path

from . import views

app_name = 'predictions'

urlpatterns = [
    path('predict/', views.predict_student, name='predict'),
    path('history/', views.prediction_history, name='history'),
    path('history/delete/<int:pk>/', views.delete_prediction, name='delete_prediction'),
    path('model-info/', views.model_info, name='model_info'),
    path('retrain/', views.retrain_model, name='retrain_model'),
    path('upload-dataset/', views.upload_dataset, name='upload_dataset'),
]
