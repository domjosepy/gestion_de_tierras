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
        # Obtener el objeto ORIGINAL de la base de datos
        original = sender.objects.get(pk=instance.pk)

        # Guardar los valores originales en el instance para uso posterior
        if not hasattr(instance, '_original_state'):
            instance._original_state = {}

        # Guardar todos los campos relevantes del original
        campos_a_auditar = ['estado', 'grupo_asignado',
                            'usuario_asignado', 'motivo_rechazo']
        for campo in campos_a_auditar:
            instance._original_state[campo] = getattr(original, campo, None)

    except sender.DoesNotExist:
        # Si no existe, es un objeto nuevo
        pass
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error obteniendo original en pre_save: {e}")


@receiver(post_save, sender=SolicitudRelevamiento)
def crear_auditoria_despues_guardar(sender, instance, created, **kwargs):
    """Crear registros de auditoría después de guardar"""
    if created:
        # Para objetos nuevos, no hacemos auditoría de cambios
        return

    # Verificar si tenemos el estado original guardado
    if not hasattr(instance, '_original_state'):
        return

    # Comparar campos con los valores originales
    campos_a_auditar = ['estado', 'grupo_asignado',
                        'usuario_asignado', 'motivo_rechazo']

    for campo in campos_a_auditar:
        valor_original = instance._original_state.get(campo)
        valor_nuevo = getattr(instance, campo, None)

        # Convertir objetos a string si es necesario
        if hasattr(valor_original, 'pk'):
            valor_original = str(valor_original)
        if hasattr(valor_nuevo, 'pk'):
            valor_nuevo = str(valor_nuevo)

        # Verificar si hubo cambio
        if valor_original != valor_nuevo:
            # Determinar quién hizo el cambio
            # Aquí necesitamos una forma de obtener el usuario que hizo el cambio
            # Podemos usar un campo en la instancia o pasar el request de alguna forma
            cambiado_por = getattr(
                instance, '_cambiado_por', None) or instance.creado_por

            # Crear registro de auditoría
            SolicitudRelevamientoAudit.objects.create(
                solicitud=instance,
                campo=campo,
                valor_anterior=str(valor_original) if valor_original else '',
                valor_nuevo=str(valor_nuevo) if valor_nuevo else '',
                cambiado_por=cambiado_por,
                comentario=f"Cambio en {campo}"
            )

    # Limpiar el estado original
    if hasattr(instance, '_original_state'):
        del instance._original_state
