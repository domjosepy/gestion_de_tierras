
from django import template
from gerencia.models import SolicitudRelevamiento

register = template.Library()


@register.filter
def estado_no_finalizado(queryset):
    """Filtra las solicitudes que NO están en estado finalizado o rechazado"""
    return queryset.exclude(estado__in=["rechazado", "finalizado"])
