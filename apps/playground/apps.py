from django.apps import AppConfig


class PlaygroundConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.playground"
    label = "playground"
    verbose_name = "Playground (pruebas de acceso)"
