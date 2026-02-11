from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect


def requiere_ser_coordinacion(user):
    """Verifica que el usuario pertenezca a coordinación"""
    if user.is_superuser:
        return True

    grupos_coordinacion = user.grupos_pertenece.filter(
        nombre__icontains='COORDINACION',
        activo=True
    ).exists()

    grupos_monitoreo = user.grupos_pertenece.filter(
        nombre__icontains='MONITOREO',
        activo=True
    ).exists()

    return grupos_coordinacion or grupos_monitoreo


def requiere_ser_lider_coordinacion(user):
    """Verifica que el usuario sea líder de coordinación"""
    if user.is_superuser:
        return True

    return user.grupos_pertenece.filter(
        nombre__icontains='COORDINACION',
        activo=True,
        lider=user
    ).exists()


# Decoradores para vistas
coordinacion_required = user_passes_test(
    lambda u: requiere_ser_coordinacion(u),
    login_url='/no-autorizado/'
)

lider_coordinacion_required = user_passes_test(
    lambda u: requiere_ser_lider_coordinacion(u),
    login_url='/no-autorizado/'
)
