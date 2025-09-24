from django.apps import AppConfig

class NotificacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.notificaciones"

    def ready(self):
        import core.notificaciones.signals
