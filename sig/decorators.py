from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from functools import wraps
from administrador.models import Grupo


def requiere_ser_sig(view_func):
    """
    Decorador que verifica si el usuario pertenece al grupo SIG
    """
    def check_sig(user):
        # Permitir siempre al superuser
        if user.is_authenticated and user.is_superuser:
            return True

        # Usamos grupos_pertenece (related_name del modelo Grupo)
        # Filtramos por grupos que contengan 'SIG' en el nombre
        if user.is_authenticated and user.grupos_pertenece.filter(nombre__icontains='SIG').exists():
            return True
        return False

    return user_passes_test(check_sig, login_url='/admin/login/')(view_func)


def requiere_ser_lider_sig(view_func):
    """
    Decorador que verifica si el usuario es líder de algún grupo SIG
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/admin/login/')

        # Verificar si es líder de algún grupo SIG
        es_lider_sig = Grupo.objects.filter(
            lider=request.user,
            nombre__icontains='SIG',
            activo=True
        ).exists()

        if es_lider_sig or request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden("No tiene permisos para acceder a esta página")

    return _wrapped_view
