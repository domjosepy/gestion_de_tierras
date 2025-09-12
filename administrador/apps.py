from django.apps import AppConfig

class AdministradorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'administrador'

    def ready(self):
        import administrador.signals 
        # Importa los signals para que se registren
        # Esto asegura que los signals se carguen cuando la app se inicie