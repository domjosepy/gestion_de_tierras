from django import template

register = template.Library()


@register.filter
def filter_attr(queryset, attr):
    """Filtra un queryset por un atributo booleano"""
    return [item for item in queryset if getattr(item, attr, False)]


@register.filter
def get_attr(obj, attr):
    """Obtiene un atributo de un objeto de forma segura"""
    return getattr(obj, attr, '')
