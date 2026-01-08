# sig/decorators.py
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from functools import wraps


def requiere_ser_sig(view_func):
    """
    Decorador que verifica si el usuario pertenece al grupo SIG
    """
    def check_sig(user):
        if user.is_authenticated and user.groups.filter(name='SIG').exists():
            return True
        return False

    return user_passes_test(check_sig, login_url='/admin/login/')(view_func)
