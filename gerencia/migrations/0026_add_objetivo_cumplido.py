# Generated manually for objetivo cumplimiento fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gerencia', '0025_alter_objetivo_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='objetivo',
            name='fecha_cumplimiento',
            field=models.DateTimeField(blank=True, help_text='Fecha en que se alcanzó el 100% de la meta', null=True, verbose_name='Fecha de Cumplimiento'),
        ),
        migrations.AddField(
            model_name='objetivo',
            name='objetivo_cumplido',
            field=models.BooleanField(default=False, help_text='Indica si el objetivo alcanzó el 100% de la meta', verbose_name='Objetivo Cumplido'),
        ),
    ]