from django.urls import path
from . import views
from . import mobile

app_name = 'grade'

urlpatterns = [
    path('mobile/', mobile.minha_grade, name='mobile'),
    path('mobile/entrar/', mobile.MobileLoginView.as_view(), name='mobile_login'),
    path('mobile/sair/', mobile.MobileLogoutView.as_view(), name='mobile_logout'),
    path('mobile/grade.pdf', mobile.baixar_pdf, name='mobile_pdf'),
    path('mobile/manifest.webmanifest', mobile.manifesto, name='mobile_manifest'),
    path('mobile/sw.js', mobile.service_worker, name='mobile_sw'),
    path('', views.exibir_grade, name='exibir_grade'),
]
