from django.http import HttpResponseForbidden
from functools import wraps

def role_required(role_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            rol = getattr(request.user, "rol", None)
            if rol and getattr(rol, "nombre", None) == role_name:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("No tiene permisos para realizar esta acción.")
        return _wrapped
    return decorator
