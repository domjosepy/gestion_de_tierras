from django.db.models.signals import post_migrate, post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.contrib.auth.models import Permission, Group
from .models import User, Rol


@receiver(post_migrate)
def crear_roles_iniciales(sender, **kwargs):

    if sender.name == 'administrador':
        roles_base = [
            {
                'nombre': 'Invitado',
                'color': 'secondary',
                'descripcion': 'Usuario registrado sin permisos especiales'
            },
            # Agrega otros roles iniciales aquí...
        ]
        for rol_data in roles_base:
            Rol.objects.get_or_create(
                # Busca sin importar mayúsculas
                nombre__iexact=rol_data['nombre'],
                defaults=rol_data  # Valores por defecto si no existe
            )


@receiver(post_save, sender=User)
def asignar_rol_por_defecto(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        # Usamos get_or_create por si acaso no existe el rol
        rol_invitado, _ = Rol.objects.get_or_create(
            nombre__iexact='Invitado',
            defaults={
                'color': 'secondary',
                'descripcion': 'Usuario registrado sin permisos especiales'
            }
        )
        instance.rol = rol_invitado
        instance.save()


@receiver(post_save, sender=Rol)
def sincronizar_rol_grupo(sender, instance, created, **kwargs):
    """Sincroniza permisos del rol con el grupo de Django"""
    if instance.grupo_django:
        # Sincronizar nombre
        instance.grupo_django.name = f"Rol_{instance.nombre}"
        instance.grupo_django.save()

        # Sincronizar permisos
        instance.sincronizar_permisos()


@receiver(m2m_changed, sender=Rol.permisos.through)
def sincronizar_permisos_rol(sender, instance, action, **kwargs):
    """Sincroniza cuando se modifican los permisos de un rol"""
    if action in ["post_add", "post_remove", "post_clear"]:
        instance.sincronizar_permisos()


@receiver(post_save, sender=User)
def sincronizar_usuario_grupos(sender, instance, created, **kwargs):
    """Sincroniza el rol del usuario con grupos de Django"""
    if instance.rol and instance.rol.grupo_django:
        # Agregar usuario al grupo de Django del rol
        instance.groups.add(instance.rol.grupo_django)

    # Si es superuser, agregar a todos los grupos
    if instance.is_superuser:
        instance.groups.add(*Group.objects.all())


@receiver(post_delete, sender=Rol)
def eliminar_grupo_asociado(sender, instance, **kwargs):
    """Elimina el grupo de Django cuando se elimina el rol"""
    if instance.grupo_django:
        instance.grupo_django.delete()
