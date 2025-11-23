from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from core.models import Departamento, Distrito, Colonia, Area, Objetivo, Solicitud, Relevamiento
from core.forms import ColoniaForm, DistritoForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.models import User, Permission
from administrador.models import Rol


# MUESTRA LA VISTA DEL ADMINISTRADOR
class GerenciaView(LoginRequiredMixin, TemplateView):
    template_name = 'gerencia/gerente_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['permisos'] = Permission.objects.all()  # Para el modal de creación de roles
        
        return context
    
# Vistas para la gestión de colonias
class ColoniaListView(LoginRequiredMixin, ListView):
    model = Colonia
    paginate_by = 25
    template_name = "gerencia/colonias_list.html"
    context_object_name = "colonias"

    def get_queryset(self):
        qs = Colonia.objects.prefetch_related("distritos").all()
        q = self.request.GET.get("q")
        estado = self.request.GET.get("estado")
        distrito = self.request.GET.get("distrito")
        if q:
            qs = qs.filter(nombre__icontains=q)
        if estado:
            qs = qs.filter(estado=estado)
        if distrito:
            qs = qs.filter(distritos__id=distrito)
        return qs.distinct()

