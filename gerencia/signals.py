from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import SolicitudRelevamiento, SolicitudRelevamientoAudit

User = get_user_model()


@receiver(pre_save, sender=SolicitudRelevamiento)
def auditar_cambios_solicitud(sender, instance, **kwargs):
    """Crear registro de auditoría para cambios importantes"""
    if not instance.pk:  # Si es nuevo, no hay auditoría previa
        return

    try:
        original = sender.objects.get(pk=instance.pk)

        # Comparar campos importantes
        campos_a_auditar = ['estado', 'grupo_asignado',
                            'usuario_asignado', 'motivo_rechazo']

        for campo in campos_a_auditar:
            valor_original = getattr(original, campo, None)
            valor_nuevo = getattr(instance, campo, None)

            # Convertir objetos a string si es necesario
            if hasattr(valor_original, 'pk'):
                valor_original = str(valor_original)
            if hasattr(valor_nuevo, 'pk'):
                valor_nuevo = str(valor_nuevo)

            if valor_original != valor_nuevo:
                # Crear registro de auditoría
                auditoria = SolicitudRelevamientoAudit(
                    solicitud=instance,
                    campo=campo,
                    valor_anterior=str(
                        valor_original) if valor_original else '',
                    valor_nuevo=str(valor_nuevo) if valor_nuevo else '',
                    cambiado_por=instance.creado_por,  # Temporal
                    comentario=f"Cambio en {campo}"
                )
                auditoria.save()

    except sender.DoesNotExist:
        pass
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error en auditoría: {e}")
