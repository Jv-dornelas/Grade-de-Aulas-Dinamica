"""Lista explícita; nunca incluir grade.urls inteiro ou o roteador da API."""
from pathlib import Path
from django.urls import include, path
from django.views.static import serve
from grade.urls import urlpatterns as rotas_grade

rotas_mobile = [r for r in rotas_grade if r.name and r.name.startswith('mobile')]
urlpatterns = [path('', include((rotas_mobile, 'grade'), namespace='grade'))]

for arquivo in ['mobile.css', 'mobile.js', 'icon-192.png', 'icon-512.png']:
    urlpatterns.append(path('static/grade/mobile/' + arquivo, serve, {
        'path': arquivo,
        'document_root': Path(__file__).resolve().parent.parent / 'grade/static/grade/mobile',
    }))
