from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from gerencia.models import SolicitudRelevamiento
from .models import OrdenTrabajo


@receiver(post_save, sender=SolicitudRelevamiento)
def notificar_coordinacion_solicitud_aprobada(sender, instance, created, **kwargs):
    """
    Notificar a coordinación cuando una solicitud es aprobada para campo
    """
    if not created and instance.estado == 'aprobado_para_campo':
        # Aquí podrías agregar lógica para notificar
        # Por ejemplo: enviar email, crear notificación, etc.
        pass


@receiver(post_save, sender=OrdenTrabajo)
def actualizar_estado_solicitud(sender, instance, created, **kwargs):
    """
    Actualizar estado de la solicitud cuando la orden cambia de estado
    """
    if instance.estado == 'completada':
        instance.solicitud.estado = 'finalizado'
        instance.solicitud.save()
    elif instance.estado == 'en_proceso':
        instance.solicitud.estado = 'en_ejecucion_campo'
        instance.solicitud.save()
