from django.shortcuts import render

from .models import Prediction


def predict(request):
    return render(request, 'predictions/predict.html')


def history(request):
    predictions = Prediction.objects.select_related('student').all()
    return render(request, 'predictions/history.html', {'predictions': predictions})
