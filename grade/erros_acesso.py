"""Recuperação de formulários expirados sem reaproveitar o POST rejeitado."""
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.cache import never_cache


@never_cache
def csrf_falhou(request, reason=''):
    mobile = request.path.startswith('/mobile/')
    destino = 'grade:mobile_login' if mobile else 'grade:inicio'
    if request.path.startswith('/admin/'):
        destino = 'admin:login'
    return render(request, 'grade/mobile/sessao_expirada.html' if mobile else 'grade/sessao_expirada.html',
                  {'url_entrar': reverse(destino)}, status=403)
