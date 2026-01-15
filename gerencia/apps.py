from django.apps import AppConfig


class GerenciaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gerencia'
    verbose_name = "Gerencia de Gestión de Tierras"

    def ready(self):
        import gerencia.signals  # Importar señales para que se registren
