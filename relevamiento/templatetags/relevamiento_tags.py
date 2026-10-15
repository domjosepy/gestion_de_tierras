from django import template

register = template.Library()


@register.filter
def get_item(obj, key):
    """Access a list by index or a dict by key."""
    try:
        return obj[key]
    except (KeyError, IndexError, TypeError):
        return None


# Ancho Bootstrap por nombre de campo
FIELD_LAYOUT = {
    # Vivienda
    'es_principal':        'col-12',
    'numero':              'col-md-4',
    'paredes':             'col-md-4',
    'piso':                'col-md-4',
    'techo':               'col-md-4',
    'piezas':              'col-md-4',
    'agua_proviene':       'col-md-4',
    'tipo_bano':           'col-md-6',
    'equipamientos':       'col-12',
    # Miembro
    'nombre_miembro':      'col-md-6',
    'ci_miembro':          'col-md-3',
    'edad_miembro':        'col-md-3',
    'sexo_miembro':        'col-md-3',
    'estado_civil_miembro':'col-md-3',
    'parentesco':          'col-md-3',
    'relacion_con_lote':   'col-md-3',
    'escolaridad':         'col-md-6',
    'grado_ano':           'col-md-6',
}

@register.filter
def col_size(field):
    return FIELD_LAYOUT.get(field.name, 'col-md-6')

@register.filter
def in_list(value, arg):
    """Devuelve True si `value` está en una lista separada por comas."""
    return value in [v.strip() for v in arg.split(',')]