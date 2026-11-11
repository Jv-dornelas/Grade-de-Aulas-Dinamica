from django.apps import AppConfig


class GradeConfig(AppConfig):
    name = 'grade'

    def ready(self):
        from . import curriculo
