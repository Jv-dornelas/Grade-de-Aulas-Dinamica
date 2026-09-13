from django.urls import path
from . import views

app_name = 'grade'

urlpatterns = [
    path('', views.exibir_grade, name='exibir_grade'),
]
