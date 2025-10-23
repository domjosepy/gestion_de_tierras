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

    template_name = "gerencia:listar_distritos.html"
    context_object_name = "distritos"

    def get_queryset(self):
        qs = Distrito.objects.prefetch_related("departamentos").all()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(nombre__icontains=q)
        return qs.distinct()

# ======================================
# Vistas para Colonias
# =======================================


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
# Crear colonia


class ColoniaCreateView(LoginRequiredMixin, CreateView):
    model = Colonia
    form_class = ColoniaForm
    template_name = "gerencia/colonia_form.html"
    success_url = reverse_lazy("gerencia:colonias_list")

# Editar colonia


class ColoniaUpdateView(LoginRequiredMixin, UpdateView):
    model = Colonia
    form_class = ColoniaForm
    template_name = "gerencia/colonia_form.html"
    success_url = reverse_lazy("gerencia:colonias_list")

# Eliminar colonia


class ColoniaDeleteView(LoginRequiredMixin, DeleteView):
    model = Colonia
    template_name = "gerencia/colonia_confirm_delete.html"
    success_url = reverse_lazy("gerencia:colonias_list")
