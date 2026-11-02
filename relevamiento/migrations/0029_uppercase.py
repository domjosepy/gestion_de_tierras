from django.db import migrations
from django.db import models


# Campos CharField con choices cuyo valor debe respetar el case original
# (minúsculas, según TIPO_REGISTRO_CHOICES, ESTADO_CARGA_CHOICES, etc.)
CAMPOS_CHOICES = [
    'tipo_registro',
    'estado_carga',
    'condicion_vivienda',
    'condicion_encuestado',
    'tipo_lote',
    'estado_civil_ocupante',
    'estado_civil_conyuge',
    'estado_entrevista',
    'sexo_ocupante',
    'sexo_conyuge',
]


def forwards(apps, schema_editor):
    Relevamiento = apps.get_model('relevamiento', 'Relevamiento')
    for campo in CAMPOS_CHOICES:
        # Bajar todo a minúsculas (los valores válidos de tus choices están en minúsculas)
        Relevamiento.objects.update(**{campo: models.functions.Lower(campo)})


def backwards(apps, schema_editor):
    # No reversible: volver a uppercasear rompería todo de nuevo
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('relevamiento', '0028_normalizar_choices_uppercase'),  # ajustá al número real
    ]
    operations = [
        migrations.RunPython(forwards, backwards),
    ]