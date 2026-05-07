from django.urls import path

from . import views

app_name = 'students'

urlpatterns = [
    path('', views.student_list, name='student_list'),
    path('<int:pk>/edit/', views.edit_registered_student, name='edit_registered_student'),
    path('<int:pk>/delete/', views.delete_registered_student, name='delete_registered_student'),
]
