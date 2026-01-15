# Standard library imports
import re

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.db.models import Count, Q
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
from gerencia.models import SolicitudRelevamiento
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
        messages.success(
            request, f'El Departamento "{departamento.nombre}" fue creado!')
        data = {
            'success': True,
            'departamento': {
                'id': departamento.id,
                'nombre': departamento.nombre
            }
        }

        if is_ajax:
            return JsonResponse(data)
        messages.success(request, data['message'])
        return redirect('gerencia:listar_departamentos')

    # Si hay errores de validación - DEVOLVER FORMATO CON errors
    if is_ajax:
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [error for error in error_list]
        return JsonResponse({'success': False, 'errors': errors}, status=400)

    # Si no es AJAX
    for error in form.errors.values():
        messages.error(request, error)
    return redirect('gerencia:listar_departamentos')


@require_POST
def editar_departamento(request, departamento_id):
    """Edita un departamento existente."""
    departamento = get_object_or_404(Departamento, id=departamento_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    form = DepartamentoForm(request.POST, instance=departamento)
    if form.is_valid():
        form.save()
        notificar_a_admins(
            mensaje=f'El Departamento "{departamento.nombre}" fue editado.',
            tipo="WARNING",
            exclude_user=request.user
        )
        msg = f'El Departamento "{departamento.nombre}" fue modificado!'
        messages.info(request, msg)
        if is_ajax:
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
    else:
        # Manejo de errores en formato consistente
        if is_ajax:
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [error for error in error_list]
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        # Si no es AJAX
        for error in form.errors.values():
            messages.error(request, error)

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
    messages.info(
        request, f'El Departamento "{departamento.nombre}" fue eliminado!')
    if is_ajax:
        return JsonResponse({'success': True, 'message': msg})
    messages.info(request, msg)
    return redirect('gerencia:listar_departamentos')


# ======================================
# FIN para Departamentos
# ======================================

# ======================================
# VISTAS para DISTRITOS
# ======================================

def listar_distritos(request):
    """Lista todos los distritos con sus departamentos"""
    distritos = Distrito.objects.select_related(
        'departamento').all().order_by('nombre')
    departamentos = Departamento.objects.all().order_by('nombre')  # Asegurar orden
    form = DistritoForm()
    return render(
        request,
        'includes/gerencia/tablas/listar_distritos.html',
        {
            'distritos': distritos,
            'departamentos': departamentos,
            'form': form
        }
    )


@require_POST
def crear_distrito(request):
    """Crea un nuevo distrito"""
    form = DistritoForm(request.POST)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if form.is_valid():
        distrito = form.save()
        messages.success(
            request, f'El Distrito "{distrito.nombre}" fue creado!')
        data = {
            'success': True,
        }

        if is_ajax:
            return JsonResponse(data)

        return redirect('gerencia:listar_distritos')

    # Manejo de errores
    if is_ajax:
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [error for error in error_list]

        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)

    # Si no es AJAX
    for error in form.errors.values():
        messages.error(request, error)

    return redirect('gerencia:listar_distritos')


@require_POST
def editar_distrito(request, pk):
    """Edita un distrito existente"""
    distrito = get_object_or_404(Distrito, pk=pk)
    form = DistritoForm(request.POST, instance=distrito)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if form.is_valid():
        distrito = form.save()

        notificar_a_admins(
            mensaje=f'El Distrito "{distrito.nombre}" fue editado.',
            tipo="WARNING",
            exclude_user=request.user
        )
        msg = f'El Distrito "{distrito.nombre}" fue modificado!'
        messages.info(request, msg)
        if is_ajax:
            return JsonResponse({'success': True, 'message': msg})
        messages.success(request, msg)
    else:
        # Manejo de errores en formato consistente
        if is_ajax:
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [error for error in error_list]
            return JsonResponse({'success': False, 'errors': errors}, status=400)

        # Si no es AJAX
        for error in form.errors.values():
            messages.error(request, error)

    return redirect('gerencia:listar_distritos')


@require_POST
def eliminar_distrito(request, pk):
    """Elimina un distrito si no tiene colonias asociadas"""
    distrito = get_object_or_404(Distrito, pk=pk)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Verificar si tiene colonias asociadas
    if distrito.colonias.exists():
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
    messages.info(request, f'El Distrito "{nombre_distrito}" fue eliminado.')
    msg = f'El Distrito "{nombre_distrito}" fue eliminado.'

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

    def get_queryset(self):
        # Anotar cada colonia con el conteo de solicitudes activas
        qs = Colonia.objects.annotate(
            num_solicitudes_activas=Count(
                'solicitudes_relevamiento',
                filter=Q(
                    solicitudes_relevamiento__estado__in=[
                        estado for estado, _ in SolicitudRelevamiento.ESTADOS
                        if estado not in ["rechazado", "finalizado"]
                    ]
                )
            )
        ).prefetch_related('distritos', 'distritos__departamento')

        # Aplicar filtros
        q = self.request.GET.get('q')
        estado = self.request.GET.get('estado')
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
        context['distritos'] = Distrito.objects.select_related(
            'departamento'
        ).order_by('departamento__nombre', 'nombre')
        context['departamentos'] = Departamento.objects.all().order_by('nombre')
        context['estado_choices'] = Colonia.ESTADO_CHOICES
        return context


@require_POST
def crear_colonia(request):
    """Crea una nueva colonia"""
    form = ColoniaForm(request.POST)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if form.is_valid():
        # Asignar código automáticamente si no se proporciona
        if not form.cleaned_data.get('codigo'):
            codigos_existentes = set(Colonia.objects.exclude(
                codigo__isnull=True).values_list('codigo', flat=True))
            codigo = 1
            while codigo in codigos_existentes:
                codigo += 1
            form.instance.codigo = codigo

        colonia = form.save()

        messages.success(request, f'La Colonia "{colonia.nombre}" fue creada!')
        data = {'success': True}

        if is_ajax:
            return JsonResponse(data)

        return redirect('gerencia:listar_colonias')

    # Manejo de errores
    if is_ajax:
        errors = {}
        for field, error_list in form.errors.items():
            # Convertir errores a lista de strings
            errors[field] = [str(error) for error in error_list]

        return JsonResponse({
            'success': False,
            'errors': errors,
            'message': 'Por favor corrige los errores en el formulario.'
        }, status=400)

    # Si no es AJAX
    for field, error_list in form.errors.items():
        for error in error_list:
            messages.error(
                request, f"{field if field != '__all__' else 'Formulario'}: {error}")

    return redirect('gerencia:listar_colonias')


@require_POST
def editar_colonia(request, colonia_id):
    """Edita una colonia existente"""
    colonia = get_object_or_404(Colonia, id=colonia_id)
    form = ColoniaForm(request.POST, instance=colonia)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if form.is_valid():
        colonia = form.save()

        messages.success(
            request, f'La Colonia "{colonia.nombre}" fue actualizada!')
        data = {'success': True}

        if is_ajax:
            return JsonResponse(data)

        return redirect('gerencia:listar_colonias')

    # Manejo de errores
    if is_ajax:
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]

        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)

    # Si no es AJAX
    for error in form.errors.values():
        messages.error(request, error)

    return redirect('gerencia:listar_colonias')


@require_POST
def eliminar_colonia(request, colonia_id):
    """Elimina una colonia si no tiene solicitudes o relevamientos asociados"""
    colonia = get_object_or_404(Colonia, id=colonia_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Verificar si tiene solicitudes o relevamientos asociados
    if colonia.solicitudes.exists() or colonia.relevamientos.exists():
        msg = f'No se puede eliminar la colonia "{colonia.nombre}" porque tiene solicitudes o relevamientos asociados.'

        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': msg
            }, status=400)

        messages.error(request, msg)
        return redirect('gerencia:listar_colonias')

    nombre_colonia = colonia.nombre
    colonia.delete()
    messages.info(request, f'La Colonia "{nombre_colonia}" fue eliminada.')
    msg = f'La Colonia "{nombre_colonia}" fue eliminada.'

    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': msg
        })

    messages.success(request, msg)
    return redirect('gerencia:listar_colonias')
