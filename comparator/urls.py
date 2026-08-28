from django.urls import path
from . import views

app_name = 'comparator'

urlpatterns = [
    path('', views.compare_resume_view, name='compare_form'),
    path('result/<int:submission_id>/', views.compare_result_view, name='compare_result'),
]
