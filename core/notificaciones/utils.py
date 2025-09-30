from django.contrib.auth import get_user_model
from .models import Notificacion

User = get_user_model()

def notificar_a_admins(mensaje, tipo="INFO", exclude_user=None, link=None):
    """
    Crea notificaciones para todos los administradores, excepto el usuario que realizó la acción.
    """
    admins = User.objects.filter(is_superuser=True)

    for admin in admins:
        if exclude_user and admin == exclude_user:
            continue
        Notificacion.objects.create(
            usuario=admin,
            mensaje=mensaje,
            tipo=tipo,
            link=link
        )
