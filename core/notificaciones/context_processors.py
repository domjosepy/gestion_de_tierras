from .models import Notificacion

def notificaciones_context(request):
    if request.user.is_authenticated:
        return {
            "notificaciones_no_leidas": Notificacion.objects.filter(
                usuario=request.user, leida=False
            ).count(),
            "notificaciones_recientes": Notificacion.objects.filter(
                usuario=request.user
            ).order_by("-creado")[:5]  # Las últimas 5 notificaciones
        }
    return {}
