from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
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
                nombre__iexact=rol_data['nombre'],  # Busca sin importar mayúsculas
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