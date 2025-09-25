from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Notificacion

@login_required
def lista_notificaciones(request):
    notificaciones = Notificacion.objects.filter(usuario=request.user)
    return render(request, "templates/includes/notificaciones/lista.html", {"notificaciones": notificaciones})


@login_required
def marcar_todas_leidas(request):
    if request.method == "POST":
        Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
        return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)