# Generated manually
from django.db import migrations, models


def migrar_tipos_objetivo(apps, schema_editor):
    """
    Migrar los valores antiguos de tipo_objetivo (CharField) a TipoObjetivo (ForeignKey).
    
    Esta migración debe ejecutarse ANTES de cambiar el campo de CharField a ForeignKey.
    """
    Objetivo = apps.get_model('gerencia', 'Objetivo')
    TipoObjetivo = apps.get_model('administrador', 'TipoObjetivo')
    Grupo = apps.get_model('administrador', 'Grupo')
    
    # Mapeo de valores antiguos a nombres de TipoObjetivo
    MAPEO_TIPOS = {
        'colonias_relevadas': 'Colonias Relevadas',
        'planos_aprobados': 'Planos Aprobados',
        'titulos_emitidos': 'Títulos Emitidos',
        'familias_beneficiadas': 'Familias Beneficiadas',
        'hectareas_regularizadas': 'Hectáreas Regularizadas',
        'audiencias_publicas': 'Audiencias Públicas',
        'consultas_atendidas': 'Consultas Atendidas',
    }
    
    # Usar SQL directo para evitar problemas con ordering y select_related
    db_alias = schema_editor.connection.alias
    
    # Obtener todos los grupos activos
    grupos = list(Grupo.objects.using(db_alias).filter(activo=True))
    
    # Primero, crear TipoObjetivo para cada grupo con todos los tipos posibles
    # Esto asegura que existan los tipos necesarios
    for grupo in grupos:
        for tipo_codigo, tipo_nombre in MAPEO_TIPOS.items():
            # Crear o obtener el TipoObjetivo
            tipo_obj, created = TipoObjetivo.objects.using(db_alias).get_or_create(
                grupo=grupo,
                nombre=tipo_nombre,
                defaults={
                    'descripcion': f'Tipo de objetivo: {tipo_nombre}',
                    'activo': True,
                }
            )
    
    # Ahora actualizar los objetivos existentes
    # Iterar manualmente sin usar queryset ordering
    with schema_editor.connection.cursor() as cursor:
        # Obtener todos los objetivos con sus valores antiguos
        cursor.execute(
            "SELECT id, grupo_id, tipo_objetivo_old FROM gerencia_objetivo WHERE tipo_objetivo_old IS NOT NULL"
        )
        objetivos_data = cursor.fetchall()
        
        for objetivo_id, grupo_id, tipo_viejo in objetivos_data:
            if tipo_viejo and tipo_viejo in MAPEO_TIPOS:
                tipo_nombre = MAPEO_TIPOS[tipo_viejo]
                try:
                    tipo_obj = TipoObjetivo.objects.using(db_alias).get(
                        grupo_id=grupo_id,
                        nombre=tipo_nombre
                    )
                    # Actualizar el objetivo directamente con SQL
                    cursor.execute(
                        "UPDATE gerencia_objetivo SET tipo_objetivo_temp_id = %s WHERE id = %s",
                        [tipo_obj.id, objetivo_id]
                    )
                except TipoObjetivo.DoesNotExist:
                    pass


def revertir_migracion(apps, schema_editor):
    """Reversa de la migración"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gerencia', '0016_add_fecha_campos_objetivo'),
        ('administrador', '0009_remove_grupo_tipos_objetivo'),
    ]

    operations = [
        # Renombrar el campo actual tipo_objetivo a tipo_objetivo_old
        migrations.RenameField(
            model_name='objetivo',
            old_name='tipo_objetivo',
            new_name='tipo_objetivo_old',
        ),
        # Agregar un campo temporal para almacenar el ID del nuevo TipoObjetivo
        migrations.AddField(
            model_name='objetivo',
            name='tipo_objetivo_temp_id',
            field=models.IntegerField(null=True, blank=True),
        ),
        # Ejecutar la función de migración de datos
        migrations.RunPython(migrar_tipos_objetivo, revertir_migracion),
    ]
