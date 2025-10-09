from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Solicitud, SolicitudAudit

@receiver(pre_save, sender=Solicitud)
def solicitud_prev_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._prev_estado = None
    else:
        try:
            prev = Solicitud.objects.get(pk=instance.pk)
            instance._prev_estado = prev.estado
        except Solicitud.DoesNotExist:
            instance._prev_estado = None

@receiver(post_save, sender=Solicitud)
def solicitud_audit(sender, instance, created, **kwargs):
    prev = getattr(instance, "_prev_estado", None)
    if created:
        SolicitudAudit.objects.create(
            solicitud=instance,
            previo="(nuevo)",
            nuevo=instance.estado,
            cambiado_por=instance.creado_por,
            comentario="Creada"
        )
    else:
        if prev is not None and prev != instance.estado:
            # Si quieres pasar usuario que hizo el cambio, la vista debe setear instance._changed_by antes de save()
            changed_by = getattr(instance, "_changed_by", None)
            SolicitudAudit.objects.create(
                solicitud=instance,
                previo=prev,
                nuevo=instance.estado,
                cambiado_por=changed_by
            )
        