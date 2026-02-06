from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Obtener un valor de un diccionario usando una clave"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def estado_icono(estado):
    """Retornar icono según estado"""
    iconos = {
        'pendiente_asignacion_sig': 'fas fa-user-clock',
        'asignado_a_digitalizador': 'fas fa-user-check',
        'en_proceso_digitalizacion': 'fas fa-spinner',
        'pendiente_revision_sig': 'fas fa-check-double',
        'pendiente_asignacion_analista': 'fas fa-check-circle',
        'en_proceso_analisis': 'fas fa-spinner',
        'pendiente_revision_analista': 'fas fa-check-double',
        'rechazado': 'fas fa-times-circle',
        'aprobado_para_campo': 'fas fa-map-marked-alt',
        'asignado_coordinacion': 'fas fa-users',
        'orden_trabajo_generada': 'fas fa-check-double',
        'preparacion_campo': 'fas fa-cogs',
        'en_ejecucion_campo': 'fas fa-walking',
        'pendiente_cierre': 'fas fa-flag-checkered',
        'finalizado': 'fas fa-flag',
    }
    return iconos.get(estado, 'fas fa-question-circle')


@register.filter
def dict_key(dictionary, key):
    """Alias para get_item para mayor claridad"""
    return get_item(dictionary, key)
