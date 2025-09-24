from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Notificacion

@login_required
def lista_notificaciones(request):
    notificaciones = Notificacion.objects.filter(usuario=request.user)
    return render(request, "templates/includes/notificaciones/lista.html", {"notificaciones": notificaciones})
