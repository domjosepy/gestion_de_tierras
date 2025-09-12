from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('administrador', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='creado_por',
            field=models.CharField(
                max_length=20,
                choices=[('usuario', 'Usuario'), ('admin', 'Administrador')],
                default='usuario',
                verbose_name='Creado por',
            ),
        ),
    ]
