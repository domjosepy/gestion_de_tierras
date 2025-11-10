# Standard library imports
import re

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView

# Local imports
from .forms import DepartamentoForm, DistritoForm, ColoniaForm
from .models import Departamento, Distrito, Colonia
from core.notificaciones.utils import notificar_a_admins


# ======================================
# Vistas para Departamentos
# =======================================

class DepartamentoListView(LoginRequiredMixin, ListView):
    model = Departamento
    template_name = 'includes/gerencia/tablas/listar_departamentos.html'
    context_object_name = 'departamentos'

    def get_queryset(self):
        # Prefetch optimiza distritos
        return Departamento.objects.prefetch_related('distritos').all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = DepartamentoForm()
        return context


@require_POST

def crear_departamento(request):
    form = DepartamentoForm(request.POST)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if form.is_valid():
        departamento = form.save()
        notificar_a_admins(
            mensaje=f'Se ha creado un nuevo Departamento: "{departamento.nombre}".',
            tipo="INFO",
            exclude_user=request.user,
            link=reverse("gerencia:listar_departamentos")
        )

        data = {
            'success': True,
            'message': f'Departamento "{departamento.nombre}" creado correctamente.',
            'departamento': {
                'id': departamento.id,
                'nombre': departamento.nombre
            }
        }

        if is_ajax:
            return JsonResponse(data)
        messages.success(request, data['message'])
        return redirect('gerencia:listar_departamentos')

    # Si hay errores de validación
    errores = form.errors.get_json_data()
    mensajes = [error['message'] for campo in errores.values() for error in campo]
    data = {'success': False, 'message': ' '.join(mensajes)}

    if is_ajax:
        return JsonResponse(data, status=400)
    messages.error(request, data['message'])
    return redirect('gerencia:listar_departamentos')


def editar_departamento(request, departamento_id):
    """Edita un departamento existente."""
    departamento = get_object_or_404(Departamento, id=departamento_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = DepartamentoForm(request.POST, instance=departamento)
        if form.is_valid():
            form.save()
            notificar_a_admins(
                mensaje=f'El Departamento "{departamento.nombre}" fue editado.',
                tipo="WARNING",
                exclude_user=request.user
            )
            msg = "Departamento modificado."
            messages.success(request, f'Departamento "{departamento.nombre}" modificado exitosamente!')
            if is_ajax:
                return JsonResponse({'success': True, 'message': msg})
            messages.success(request, msg)
        else:
            msg = " ".join([err for errs in form.errors.values() for err in errs])
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.error(request, msg)
        return redirect('gerencia:listar_departamentos')

    return redirect('gerencia:listar_departamentos')


@require_POST
def eliminar_departamento(request, departamento_id):
    """Elimina un departamento si no tiene distritos asociados."""
    departamento = get_object_or_404(Departamento, id=departamento_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if departamento.distritos.exists():
        msg = "No se puede eliminar: el Departamento tiene Distritos asociados."
        if is_ajax:
            return JsonResponse({'success': False, 'message': msg}, status=400)
        messages.error(request, msg)
        return redirect('gerencia:listar_departamentos')

    departamento.delete()
    msg = "Departamento eliminado correctamente."
    messages.success(request, f'Departamento "{departamento.nombre}" eliminado exitosamente!')
    if is_ajax:
        return JsonResponse({'success': True, 'message': msg})
    messages.success(request, msg)
    return redirect('gerencia:listar_departamentos')



# ======================================
# FIN para Departamentos
# ======================================

# ======================================
# VISTAS para DISTRITOS
# ======================================

def listar_distritos(request):
    """Lista todos los distritos con sus departamentos"""
    distritos = Distrito.objects.select_related('departamento').all().order_by('nombre')
    departamentos = Departamento.objects.all()
    form = DistritoForm()
    return render(
        request,
        'includes/gerencia/tablas/listar_distritos.html',
        {'distritos': distritos, 'departamentos': departamentos, 'form': form}
    )


@require_POST
def crear_distrito(request):
    """Crea un nuevo distrito"""
    form = DistritoForm(request.POST)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if form.is_valid():
        distrito = form.save()
        
        data = {
            'success': True,
            'message': f'Distrito "{distrito.nombre}" creado correctamente.',
            'distrito': {
                'id': distrito.id,
                'nombre': distrito.nombre,
                'codigo': distrito.codigo,
                'departamento': distrito.departamento.nombre
            }
        }

        if is_ajax:
            return JsonResponse(data)
        
        messages.success(request, data['message'])
        return redirect('gerencia:listar_distritos')

    # Si hay errores de validación
    if is_ajax:
        # Devolver errores en formato JSON
        errores = {}
        for field, errors in form.errors.items():
            errores[field] = [str(error) for error in errors]
        
        return JsonResponse({
            'success': False,
            'errors': errores
        }, status=400)
    
    # Si no es AJAX, mostrar errores como mensajes
    for field, errors in form.errors.items():
        for error in errors:
            messages.error(request, f'{field}: {error}')
    
    return redirect('gerencia:listar_distritos')


@require_POST
def editar_distrito(request, pk):
    """Edita un distrito existente"""
    distrito = get_object_or_404(Distrito, pk=pk)
    form = DistritoForm(request.POST, instance=distrito)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if form.is_valid():
        distrito = form.save()
        
        data = {
            'success': True,
            'message': f'Distrito "{distrito.nombre}" actualizado correctamente.'
        }

        if is_ajax:
            return JsonResponse(data)
        
        messages.success(request, data['message'])
        return redirect('gerencia:listar_distritos')

    # Si hay errores de validación
    if is_ajax:
        # Devolver errores en formato JSON
        errores = {}
        for field, errors in form.errors.items():
            errores[field] = [str(error) for error in errors]
        
        # Si hay errores de validación cruzada (__all__)
        if '__all__' in errores:
            return JsonResponse({
                'success': False,
                'message': ' '.join(errores['__all__'])
            }, status=400)
        
        return JsonResponse({
            'success': False,
            'errors': errores
        }, status=400)
    
    # Si no es AJAX, mostrar errores como mensajes
    for field, errors in form.errors.items():
        for error in errors:
            messages.error(request, f'{field}: {error}')
    
    return redirect('gerencia:listar_distritos')


@require_POST
def eliminar_distrito(request, pk):
    """Elimina un distrito si no tiene colonias asociadas"""
    distrito = get_object_or_404(Distrito, pk=pk)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Verificar si tiene colonias asociadas
    if distrito.colonias.exists():
        messages.danger(request, "No se puede eliminar: el Distrito tiene Colonias asociadas.")
        msg = f'No se puede eliminar el distrito "{distrito.nombre}" porque tiene {distrito.colonias.count()} colonia(s) asociada(s).'
        
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': msg
            }, status=400)
        
        messages.error(request, msg)
        return redirect('gerencia:listar_distritos')

    nombre_distrito = distrito.nombre
    distrito.delete()
    messages.success(request, f'Distrito "{nombre_distrito}" eliminado exitosamente!')
    msg = f'Distrito "{nombre_distrito}" eliminado correctamente.'
    
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': msg
        })
    
    messages.success(request, msg)
    return redirect('gerencia:listar_distritos')

# ======================================
# Vistas para Colonias
# =======================================

class ColoniaListView(LoginRequiredMixin, ListView):
    model = Colonia
    paginate_by = 25
    template_name = 'includes/gerencia/tablas/listar_colonias.html'
    context_object_name = 'colonias'
    form_class = ColoniaForm

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
