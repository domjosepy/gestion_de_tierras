from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from functools import wraps
from administrador.models import Grupo


def requiere_ser_analisis(view_func):
    """
    Decorador que verifica si el usuario pertenece al grupo ANALISIS
    """
    def check_analisis(user):
        # Permitir siempre al superuser
        if user.is_authenticated and user.is_superuser:
            return True

        # Usamos grupos_pertenece (related_name del modelo Grupo)
        # Filtramos por grupos que contengan 'ANALISIS' en el nombre
        if user.is_authenticated and user.grupos_pertenece.filter(nombre__icontains='ANALISIS').exists():
            return True
        return False

    return user_passes_test(check_analisis, login_url='/admin/login/')(view_func)


def requiere_ser_lider_analisis(view_func):
    """
    Decorador que verifica si el usuario es líder de algún grupo ANALISIS
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/admin/login/')

        # Verificar si es líder de algún grupo ANALISIS
        es_lider_analisis = Grupo.objects.filter(
            lider=request.user,
            nombre__icontains='ANALISIS',
            activo=True
        ).exists()

        if es_lider_analisis or request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden("No tiene permisos para acceder a esta página")

    return _wrapped_view
