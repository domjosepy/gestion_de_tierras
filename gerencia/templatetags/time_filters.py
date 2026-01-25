from django import template
from django.utils import timezone
from django.utils.timesince import timesince
import datetime

register = template.Library()


@register.filter
def format_timedelta(td):
    """Formatea un timedelta a texto legible"""
    if not isinstance(td, datetime.timedelta):
        return td

    # Si es menos de 1 día
    if td.days == 0:
        horas = td.seconds // 3600
        minutos = (td.seconds % 3600) // 60

        if horas > 0:
            return f"{horas}h {minutos}m"
        elif minutos > 0:
            return f"{minutos}m"
        else:
            return "Recién"

    # Si es 1 día o más
    if td.days == 1:
        return "1 día"
    else:
        return f"{td.days} días"


@register.filter
def time_since_detail(datetime_obj):
    """Muestra tiempo desde una fecha específica con detalles"""

    if not datetime_obj:
        return "Nunca"

    now = timezone.now()
    diff = now - datetime_obj

    if diff.days == 0:
        if diff.seconds < 60:
            return "Recién"
        elif diff.seconds < 3600:
            minutos = diff.seconds // 60
            return f"{minutos}m"
        else:
            horas = diff.seconds // 3600
            minutos = (diff.seconds % 3600) // 60
            return f"{horas}h {minutos}m"
    elif diff.days == 1:
        return "1 día"
    else:
        return f"{diff.days} días"
