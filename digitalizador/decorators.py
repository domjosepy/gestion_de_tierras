# digitalizador/decorators.py
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from functools import wraps


def requiere_ser_digitalizador(view_func):
    """
    Decorador que verifica si el usuario es digitalizador
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return user_passes_test(lambda u: False, login_url='/admin/login/')(view_func)(request, *args, **kwargs)

        # Verificar si es superusuario
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Verificar si está asignado a alguna tarea como digitalizador
        from gerencia.models import SolicitudRelevamiento
        es_digitalizador_asignado = SolicitudRelevamiento.objects.filter(
            usuario_digitalizador=request.user
        ).exists()

        # Verificar si pertenece a grupo SIG
        en_grupo_sig = request.user.grupos_pertenece.filter(
            nombre__icontains='SIG',
            activo=True
        ).exists()

        # Verificar si tiene permisos específicos
        tiene_permisos = request.user.has_perm('gerencia.cambiar_estado') or \
            request.user.has_perm('digitalizador.puede_acceder')

        if not (es_digitalizador_asignado or en_grupo_sig or tiene_permisos):
            return HttpResponseForbidden("No tiene permisos para acceder a esta sección.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view
