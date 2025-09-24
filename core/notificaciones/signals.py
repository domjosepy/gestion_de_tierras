from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from core.notificaciones.models import Notificacion

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def notificar_usuario_creado(sender, instance, created, **kwargs):
    if created:
        # Notificación genérica al administrador
        Notificacion.objects.create(
            usuario=instance,
            mensaje=f"Se creó el usuario {instance.username}",
            tipo="SUCCESS"
        )
        # Notificación específica al usuario creado