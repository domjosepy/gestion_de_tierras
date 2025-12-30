# gerencia/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import SolicitudRelevamiento, SolicitudRelevamientoAudit

@receiver(pre_save, sender=SolicitudRelevamiento)
def solicitud_prev_state(sender, instance, **kwargs):
    """
    Guarda el estado previo antes de actualizar la solicitud.
    """
    if not instance.pk:
        instance._prev_estado = None
    else:
        try:
            prev = SolicitudRelevamiento.objects.get(pk=instance.pk)
            instance._prev_estado = prev.estado
        except SolicitudRelevamiento.DoesNotExist:
            instance._prev_estado = None

@receiver(post_save, sender=SolicitudRelevamiento)
def solicitud_audit(sender, instance, created, **kwargs):
    """
    Crea un registro de auditoría cada vez que se crea o cambia el estado.
    """
    prev = getattr(instance, "_prev_estado", None)
    if created:
        SolicitudRelevamientoAudit.objects.create(
            solicitud=instance,
            previo="(nuevo)",
            nuevo=instance.estado,
            cambiado_por=instance.creado_por,
            comentario="Creada"
        )
    else:
        if prev is not None and prev != instance.estado:
            changed_by = getattr(instance, "_changed_by", None)
            SolicitudRelevamientoAudit.objects.create(
                solicitud=instance,
                previo=prev,
                nuevo=instance.estado,
                cambiado_por=changed_by,
                comentario=f"Estado cambiado de {prev} a {instance.estado}"
            )
