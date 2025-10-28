from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse, reverse_lazy
from django.db.models import Q
from .models import Departamento, Distrito, Colonia
from .forms import ColoniaForm, DistritoForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from core.notificaciones.utils import notificar_a_admins

# ======================================
# Vistas para Departamentos
# =======================================



class DepartamentoListView(LoginRequiredMixin, ListView):
    model = Departamento
    template_name = 'includes/gerencia/tablas/listar_departamentos.html'
    context_object_name = 'departamentos'

    def get_queryset(self):
        # Optimizar consulta contando distritos
        return Departamento.objects.prefetch_related('distritos').all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departamentos'] = Departamento.objects.all()
        return context

class DepartamentoCreateView(LoginRequiredMixin, CreateView):
    model = Departamento
    fields = ['nombre']
    template_name = 'includes/gerencia/modal/departamentos/crear_departamento_modal.html'

    def get_success_url(self):
        # Redirige a la página anterior si existe, si no a listar_departamentos
        return self.request.META.get('HTTP_REFERER', str(reverse_lazy('gerencia:listar_departamentos')))

    def form_valid(self, form):
        # Buscar el menor número faltante (antes de guardar)
        codigos_existentes = set(
            Departamento.objects.values_list('codigo', flat=True))
        codigo = 1
        while codigo in codigos_existentes:
            codigo += 1
        form.instance.codigo = codigo  # asignar el primer número libre

        response = super().form_valid(form)

        messages.success(
            self.request, f'Departamento "{self.object.nombre}" creado exitosamente!'
        )

        # Notifica a los administradores sobre el nuevo departamento creado
        notificar_a_admins(
            mensaje=f'Se ha creado un nuevo Departamento: "{self.object.nombre}".',
            tipo="INFO",
            exclude_user=self.request.user,  # si el creador es admin no se notifica a sí mismo
            # Enlace directo al listado
            link=reverse("gerencia:listar_departamentos")
        )

        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            'Error al crear el departamento. Por favor revise los datos.'
        )
        return super().form_invalid(form)


def editar_departamento(request, departamento_id):
    departamento = get_object_or_404(Departamento, id=departamento_id)
    if request.method == 'POST':
        departamento.codigo = request.POST.get('codigo')
        departamento.nombre = request.POST.get('nombre')
        departamento.save()
        messages.success(request, "Departamento actualizado correctamente.")
        notificar_a_admins(
            mensaje=f'El Departamento "{departamento.nombre}" fue editado.',
            tipo="WARNING",
            exclude_user=request.user
        )
        return redirect('gerencia:listar_departamentos')
    return redirect('gerencia:listar_departamentos')


def eliminar_departamento(request, departamento_id):
    departamento = get_object_or_404(Departamento, id=departamento_id)
    if departamento.distritos.exists():  # Verifica si el departamento está asignado a algún distrito
        messages.error(
            request, "Este Departamento está asignado a uno o más Distritos y no puede ser eliminado.")
    else:
        departamento.delete()
        messages.success(request, "Departamento eliminado correctamente.")
    return redirect('gerencia:listar_departamentos')


# ======================================
# FIN para Departamentos
# ======================================

# ======================================
# VISTAS para DISTRITOS
# ======================================


class DistritoListView(LoginRequiredMixin, ListView):
    model = Distrito
    paginate_by = 25
    template_name = 'includes/gerencia/tablas/listar_distritos.html'
    context_object_name = 'distritos'

    def get_queryset(self):
        # Optimizar consultas relacionadas
        qs = Distrito.objects.select_related('departamento').prefetch_related('colonias')

        # Filtros existentes...
        departamento_id = self.request.GET.get('departamento')
        q = self.request.GET.get('q')

        if departamento_id:
            qs = qs.filter(departamento_id=departamento_id)
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q) |
                Q(departamento__nombre__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departamentos'] = Departamento.objects.all()
        return context

class DistritoCreateView(LoginRequiredMixin, CreateView):
    model = Distrito
    fields = ['nombre', 'departamento']
    template_name = 'includes/gerencia/modal/distritos/crear_distrito_modal.html'

    def get_success_url(self):
        return reverse_lazy('gerencia:listar_distritos')

    def form_valid(self, form):
        # Buscar el menor número faltante (antes de guardar)
        codigos_existentes = set(
            Distrito.objects.values_list('codigo', flat=True))
        codigo = 1
        while codigo in codigos_existentes:
            codigo += 1
        form.instance.codigo = codigo  # asignar el primer número libre

        response = super().form_valid(form)

        try:
            response = super().form_valid(form)
            messages.success(
                self.request, 
                f'Distrito "{self.object.nombre}" creado exitosamente!'
            )
            
            return response
        except Exception as e:
            
            messages.error(self.request, f"Error al crear distrito: {e}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        
        messages.error(
            self.request,
            'Error al crear el distrito. Por favor revise los datos.'
        )
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departamentos'] = Departamento.objects.all()
        return context

def editar_distrito(request, distrito_id):
    distrito = get_object_or_404(Distrito, id=distrito_id)
    if request.method == 'POST':
        form = DistritoForm(request.POST, instance=distrito)
        if form.is_valid():
            form.save()
            messages.success(request, "Distrito actualizado correctamente.")
            
            # Para AJAX
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Distrito actualizado correctamente.'
                })
        else:
            messages.error(request, "Error al actualizar el distrito.")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
        
        # Redirección normal para requests no-AJAX
        return redirect('gerencia:listar_distritos')
    return redirect('gerencia:listar_distritos')

def eliminar_distrito(request, distrito_id):
    distrito = get_object_or_404(Distrito, id=distrito_id)
    if distrito.colonias.exists():
        messages.error(
            request,
            "Este Distrito está asignado a una o más Colonias y no puede ser eliminado."
        )
    else:
        distrito.delete()
        messages.success(request, "Distrito eliminado correctamente.")
    return redirect('gerencia:listar_distritos')

# ======================================
# Vistas para Colonias
# =======================================

class ColoniaListView(LoginRequiredMixin, ListView):
    model = Colonia
    paginate_by = 25
    template_name = 'includes/gerencia/tablas/listar_colonias.html'
    context_object_name = 'colonias'

    def get_queryset(self):
        # Optimizar consultas relacionadas
        qs = Colonia.objects.prefetch_related('solicitudes').all()

        q = self.request.GET.get('q')
        estado = self.request.GET.get('estado')
        departamento_id = self.request.GET.get('departamento')  
        distrito_id = self.request.GET.get('distrito')

        if q:
            qs = qs.filter(nombre__icontains=q)
        if estado:
            qs = qs.filter(estado=estado)
        if distrito_id:
            qs = qs.filter(distritos__id=distrito_id)

        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['distritos'] = Distrito.objects.all()
        context['estado_choices'] = Colonia.ESTADO_CHOICES
        return context


class ColoniaCreateView(LoginRequiredMixin, CreateView):
    model = Colonia
    form_class = ColoniaForm
    template_name = 'includes/gerencia/modal/colonias/crear_colonia_modal.html'

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', reverse_lazy('gerencia:listar_colonias'))

    def form_valid(self, form):
        response = super().form_valid(form)

        # Buscar el menor número faltante (antes de guardar)
        codigos_existentes = set(
            Colonia.objects.values_list('codigo', flat=True))
        codigo = 1
        while codigo in codigos_existentes:
            codigo += 1
        form.instance.codigo = codigo  # asignar el primer número libre

        response = super().form_valid(form)
        
        # Si viene de un distrito específico, asegurarnos de que esté asignado
        distrito_id = self.request.POST.get('distritos')
        if distrito_id:
            try:
                distrito = Distrito.objects.get(id=distrito_id)
                self.object.distritos.add(distrito)
            except Distrito.objects.DoesNotExist:
                pass
        
        messages.success(
            self.request,
            f'Colonia "{self.object.nombre}" creada exitosamente!'
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            'Error al crear la colonia. Por favor revise los datos.'
        )
        return super().form_invalid(form)


def editar_colonia(request, colonia_id):
    colonia = get_object_or_404(Colonia, id=colonia_id)
    if request.method == 'POST':
        # Para ManyToMany fields, necesitamos usar el form
        form = ColoniaForm(request.POST, instance=colonia)
        if form.is_valid():
            form.save()
            messages.success(request, "Colonia actualizada correctamente.")
        else:
            messages.error(request, "Error al actualizar la colonia.")
        return redirect('gerencia:listar_colonias')
    return redirect('gerencia:listar_colonias')


def eliminar_colonia(request, colonia_id):
    colonia = get_object_or_404(Colonia, id=colonia_id)
    if colonia.solicitudes.exists() or colonia.relevamientos.exists():
        messages.error(
            request,
            "Esta Colonia tiene solicitudes o relevamientos asociados y no puede ser eliminada."
        )
    else:
        colonia.delete()
        messages.success(request, "Colonia eliminada correctamente.")
    return redirect('gerencia:listar_colonias')
