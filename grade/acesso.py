"""Entrada do sistema com contas individuais do Django e permissões existentes."""
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseNotAllowed
from django.urls import reverse_lazy

from .dashboard import inicio as painel


class AcessoForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise self.get_invalid_login_error()


class EntradaView(LoginView):
    template_name = 'grade/login_grade.html'
    authentication_form = AcessoForm
    next_page = reverse_lazy('grade:inicio')

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_active and request.user.is_staff:
            return painel(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_active and request.user.is_staff:
            return HttpResponseNotAllowed(['GET'])
        return super().post(request, *args, **kwargs)


class SaidaView(LogoutView):
    next_page = reverse_lazy('grade:inicio')
