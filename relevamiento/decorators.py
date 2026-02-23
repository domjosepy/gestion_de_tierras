from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def is_encuestador(user):
    """
    Retorna True si el usuario es superuser o tiene el rol ENCUESTADOR
    (detectado por el grupo Django 'Rol_ENCUESTADOR' creado por el modelo Rol).
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # Verificación por el modelo `Grupo` (campo `grupos_pertenece`) — consistente con coordinacion.decorators
    try:
        if user.grupos_pertenece.filter(nombre__icontains='ENCUESTADOR', activo=True).exists():
            return True
    except Exception:
        # Si el atributo no existe por alguna razón, caeremos al chequeo por rol
        pass
    # Verificación directa por el FK rol en el modelo User
    return bool(user.rol and user.rol.nombre.upper() == 'ENCUESTADOR')


def encuestador_required(view_func):
    """
    Decorador que restringe el acceso a usuarios con rol ENCUESTADOR.
    Además verifica que el usuario está asignado a la orden cuando viene
    la kwarg `orden_id` en la URL.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Al igual que en `coordinacion.decorators`, dejamos la gestión de
        # acceso a `user_passes_test` para rutas públicas; aquí validamos
        # que el usuario esté autenticado y tenga el rol de encuestador.
        if not request.user.is_authenticated:
            return redirect('/accounts/login/')

        if not is_encuestador(request.user):
            # Para consistencia con coordinacion, devolvemos 403 cuando el
            # usuario no pertenece al grupo/rol necesario.
            raise PermissionDenied("No tiene permisos de encuestador.")

        # Si la URL incluye orden_id, verificar que el encuestador pertenece a esa orden
        orden_id = kwargs.get('orden_id')
        if orden_id:
            from coordinacion.models import OrdenTrabajo
            try:
                orden = OrdenTrabajo.objects.get(pk=orden_id)
            except OrdenTrabajo.DoesNotExist:
                raise PermissionDenied("La orden de trabajo no existe.")

            # Verificar que el usuario es encuestador en algún equipo de la orden
            asignado = orden.equipos_asignados.filter(
                encuestadores=request.user
            ).exists()

            if not asignado and not request.user.is_superuser:
                raise PermissionDenied(
                    "No está asignado como encuestador a esta orden de trabajo."
                )

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def is_coordinador_campo(user):
    """
    Retorna True si el usuario es superuser o tiene el rol COORDINADOR_CAMPO
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    # Verificación por el modelo `Grupo` (campo `grupos_pertenece`)
    try:
        if user.grupos_pertenece.filter(nombre__icontains='COORDINADOR', activo=True).exists():
            return True
    except Exception:
        pass
    # Verificación directa por el FK rol en el modelo User
    return bool(user.rol and 'COORDINADOR' in user.rol.nombre.upper())


def coordinador_campo_required(view_func):
    """
    Decorador que restringe el acceso a usuarios con rol COORDINADOR_CAMPO.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/accounts/login/')

        if not is_coordinador_campo(request.user):
            raise PermissionDenied("No tiene permisos de coordinador de campo.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view
