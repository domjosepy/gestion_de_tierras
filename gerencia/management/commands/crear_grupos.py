from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from gerencia.models import SolicitudRelevamiento


class Command(BaseCommand):
    help = 'Crea grupos SIG, Digitalizador y Analista con sus permisos'

    def handle(self, *args, **options):
        self.stdout.write('🚀 Creando grupos y permisos...')

        # Crear grupos
        for nombre in ['SIG', 'Digitalizador', 'Analista']:
            grupo, creado = Group.objects.get_or_create(name=nombre)
            if creado:
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Grupo {nombre} creado'))
            else:
                self.stdout.write(self.style.WARNING(
                    f'⚠️ Grupo {nombre} ya existía'))

        # Obtener permisos
        content_type = ContentType.objects.get_for_model(SolicitudRelevamiento)
        permisos = Permission.objects.filter(content_type=content_type)

        # Asignar permisos
        grupo_sig = Group.objects.get(name='SIG')
        grupo_sig.permissions.set(permisos.filter(codename__in=[
            'view_solicitudrelevamiento', 'change_solicitudrelevamiento',
            'add_solicitudrelevamiento', 'delete_solicitudrelevamiento',
        ]))

        grupo_dig = Group.objects.get(name='Digitalizador')
        grupo_dig.permissions.set(permisos.filter(codename__in=[
            'view_solicitudrelevamiento', 'change_solicitudrelevamiento',
        ]))

        grupo_ana = Group.objects.get(name='Analista')
        grupo_ana.permissions.set(permisos.filter(codename__in=[
            'view_solicitudrelevamiento', 'change_solicitudrelevamiento',
        ]))

        self.stdout.write(self.style.SUCCESS(
            '\n🎉 Grupos y permisos configurados exitosamente!'))
