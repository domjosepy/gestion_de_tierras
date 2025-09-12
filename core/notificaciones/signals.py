from django.db.models.signals import post_save
from django.dispatch import receiver
from administrador.models import User
from .models import Notificacion

@receiver(post_save, sender=User)
def notificar_registro_usuario(sender, instance, created, **kwargs):
    if created and instance.estado == 'PENDIENTE':
        Notificacion.notificar_nuevo_usuario(instance)