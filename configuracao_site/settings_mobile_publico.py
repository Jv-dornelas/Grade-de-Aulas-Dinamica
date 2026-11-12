"""Entrada de demonstração isolada: somente portal mobile, sem gestão pública."""
from .settings import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ['.trycloudflare.com', 'localhost', '127.0.0.1']
ROOT_URLCONF = 'configuracao_site.urls_mobile_publico'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_NAME = 'mobile_publico_session'
CSRF_COOKIE_NAME = 'mobile_publico_csrf'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
