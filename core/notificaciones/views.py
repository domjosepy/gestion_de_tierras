from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notificacion

@login_required
def lista_notificaciones(request):
    notificaciones = Notificacion.objects.filter(usuario=request.user)
    return render(request, "includes/notificaciones/lista.html", {"notificaciones": notificaciones})

@login_required
def marcar_todas_leidas(request):
    Notificacion.objects.filter(usuario=request.user, leida=False).update(leida=True)
    return redirect(request.META.get("HTTP_REFERER", "notificaciones:lista"))

@login_required
def eliminar_notificacion(request, pk):
    noti = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
    noti.delete()
    return redirect("notificaciones:lista")

@login_required
def eliminar_seleccionadas(request):
    if request.method == "POST":
        ids = request.POST.getlist("seleccionadas")
        Notificacion.objects.filter(usuario=request.user, id__in=ids).delete()
    return redirect("notificaciones:lista")

@login_required
def eliminar_todas(request):
    Notificacion.objects.filter(usuario=request.user).delete()
    return redirect("notificaciones:lista")
