from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from functools import wraps


def requiere_ser_digitalizador(view_func):
    """
    Decorador que verifica si el usuario es digitalizador
    (usuario asignado a una tarea de digitalización)
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return user_passes_test(lambda u: False, login_url='/admin/login/')(view_func)(request, *args, **kwargs)

        # Verificar si es superusuario o tiene permiso específico
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Verificar si está asignado a alguna tarea de digitalización
        from gerencia.models import SolicitudRelevamiento
        tiene_tareas = SolicitudRelevamiento.objects.filter(
            usuario_asignado=request.user,
            estado__in=['asignado_a_digitalizador',
                        'en_proceso_digitalizacion', 'pendiente_revision_sig']
        ).exists()

        # Verificar si pertenece a grupo SIG
        en_grupo_sig = request.user.grupos_pertenece.filter(
            nombre__icontains='SIG',
            activo=True
        ).exists()

        if not (tiene_tareas or en_grupo_sig):
            return HttpResponseForbidden("No tiene permisos para acceder a esta sección.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view
