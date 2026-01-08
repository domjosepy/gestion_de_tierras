# digitalizador/decorators.py
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from functools import wraps


def requiere_ser_digitalizador(view_func):
    """
    Decorador que verifica si el usuario pertenece al grupo Digitalizador
    """
    def check_digitalizador(user):
        if user.is_authenticated and user.groups.filter(name='Digitalizador').exists():
            return True
        return False

    return user_passes_test(check_digitalizador, login_url='/admin/login/')(view_func)
