from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden

from functools import wraps


def requiere_ser_analista(view_func):
    """
    Decorador que verifica si el usuario pertenece al grupo analista
    """
    def check_analista(user):
        if user.is_authenticated and user.groups.filter(name='Analista').exists():
            return True
        return False

    return user_passes_test(check_analista, login_url='/admin/login/')(view_func)
