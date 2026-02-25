# Generated manually
import django.db.models.deletion
from django.db import migrations, models


def copiar_temp_id_a_fk(apps, schema_editor):
    """
    Copiar los IDs temporales al nuevo campo ForeignKey
    """
    Objetivo = apps.get_model('gerencia', 'Objetivo')
    TipoObjetivo = apps.get_model('administrador', 'TipoObjetivo')
    
    for objetivo in Objetivo.objects.all():
        if hasattr(objetivo, 'tipo_objetivo_temp_id') and objetivo.tipo_objetivo_temp_id:
            try:
                tipo_obj = TipoObjetivo.objects.get(id=objetivo.tipo_objetivo_temp_id)
                objetivo.tipo_objetivo = tipo_obj
                objetivo.save()
            except TipoObjetivo.DoesNotExist:
                pass


def reversa(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('gerencia', '0017_migrar_datos_tipo_objetivo'),
        ('administrador', '0009_remove_grupo_tipos_objetivo'),
    ]

    operations = [
        # Agregar el nuevo campo ForeignKey (nullable por ahora)
        migrations.AddField(
            model_name='objetivo',
            name='tipo_objetivo',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='objetivos',
                to='administrador.tipoobjetivo',
                verbose_name='Tipo de Objetivo',
                help_text='Seleccione el tipo de objetivo del grupo'
            ),
        ),
        # Copiar los datos del campo temporal al nuevo ForeignKey
        migrations.RunPython(copiar_temp_id_a_fk, reversa),
        # Eliminar los campos temporales
        migrations.RemoveField(
            model_name='objetivo',
            name='tipo_objetivo_old',
        ),
        migrations.RemoveField(
            model_name='objetivo',
            name='tipo_objetivo_temp_id',
        ),
        # Hacer el campo tipo_objetivo no nullable
        migrations.AlterField(
            model_name='objetivo',
            name='tipo_objetivo',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='objetivos',
                to='administrador.tipoobjetivo',
                verbose_name='Tipo de Objetivo',
                help_text='Seleccione el tipo de objetivo del grupo'
            ),
        ),
    ]
