from django.contrib import admin
from django.urls import path
from grade.views import exibir_grade # Importamos a nossa view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('grade/', exibir_grade, name='exibir_grade'), # Nova rota criada!
]