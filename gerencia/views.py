from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from core.models import Departamento, Distrito, Colonia
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

        # 👉 Agregamos los QuerySets para que el template pueda contar
        context['departamentos'] = Departamento.objects.all()
        context['distritos'] = Distrito.objects.all()
        context['colonias'] = Colonia.objects.all()
        
       # context['objetivos'] = Objetivo.objects.all()
        #context['solicitudes'] = Solicitud.objects.all()
        #context['relevamientos'] = Relevamiento.objects.all()

        return context


