from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from core.models import Departamento, Distrito, Colonia
from core.forms import ColoniaForm, DistritoForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.models import User, Permission
from administrador.models import Rol
from gerencia.models import SolicitudRelevamiento
from gerencia.forms import SolicitudRelevamientoForm, EditarSolicitudRelevamientoForm


# MUESTRA LA VISTA DEL ADMINISTRADOR
class GerenciaView(LoginRequiredMixin, TemplateView):
    template_name = 'gerencia/gerente_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Para el modal de creación de roles
        context['permisos'] = Permission.objects.all()

        # Agregamos los QuerySets para que el template pueda contar
        context['departamentos'] = Departamento.objects.all()
        context['distritos'] = Distrito.objects.all()
        context['colonias'] = Colonia.objects.all()

       # context['objetivos'] = Objetivo.objects.all()
        # context['solicitudes'] = Solicitud.objects.all()
        # context['relevamientos'] = Relevamiento.objects.all()

        return context

# LISTA TODAS LAS SOLICITUDES (sin parámetro)


def lista_solicitudes_relevamiento(request):
    """
    Lista todas las solicitudes de relevamiento con información de departamento y distrito
    """
    # Optimizar las consultas
    solicitudes = SolicitudRelevamiento.objects.select_related(
        "colonia", "creado_por"
    ).prefetch_related(
        "colonia__distritos__departamento"
    ).all()

    # Agregar información adicional a cada solicitud
    for solicitud in solicitudes:
        distritos = solicitud.colonia.distritos.all()
        if distritos.exists():
            distrito = distritos.first()
            solicitud.distrito = distrito
            solicitud.departamento = distrito.departamento
        else:
            solicitud.distrito = None
            solicitud.departamento = None

    # Obtener mensaje toast de la sesión si existe
    toast_message = request.session.pop(
        'toast_message', None) if request.session else None

    return render(request, "includes/gerencia/tablas/listar_solicitud_relevamiento.html", {
        "solicitudes": solicitudes,
        "toast_message": toast_message
    })

# OBTENER DATOS DE UNA SOLICITUD PARA EDITAR (con parámetro pk)


def obtener_datos_solicitud(request, pk):
    """Obtener datos COMPLETOS de una solicitud para editar (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, pk=pk)
    if not solicitud.puede_editar():
        return JsonResponse({'error': 'No se puede editar esta solicitud'}, status=403)

    # Obtener información jerárquica
    colonia = solicitud.colonia
    distrito = colonia.distritos.first() if colonia.distritos.exists() else None
    departamento = distrito.departamento if distrito else None

    data = {
        'success': True,
        'colonia': {
            'nombre': colonia.nombre,
            'codigo': colonia.codigo
        },
        'distrito': {
            'nombre': distrito.nombre if distrito else "Sin distrito",
            'codigo': distrito.codigo if distrito else ""
        },
        'departamento': {
            'nombre': departamento.nombre if departamento else "Sin departamento",
            'codigo': departamento.codigo if departamento else ""
        },
        'estado_display': solicitud.get_estado_display(),
        'tipo_display': solicitud.get_tipo_display(),
        'observaciones': solicitud.observaciones
    }
    return JsonResponse(data)


def crear_solicitud_relevamiento(request, colonia_id):
    colonia = get_object_or_404(Colonia, pk=colonia_id)

    if request.method == "POST":
        form = SolicitudRelevamientoForm(request.POST)
        if form.is_valid():
            try:
                solicitud = form.save(commit=False)
                solicitud.colonia = colonia
                solicitud.creado_por = request.user
                solicitud.save()

                # Guardar mensaje para toast en sesión
                request.session['toast_message'] = {
                    'text': f'Solicitud {solicitud.colonia.nombre} creada.',
                    'type': 'success'
                }

                return JsonResponse({
                    "success": True,
                    "message": "Solicitud creada exitosamente",
                    "solicitud_id": solicitud.id,
                    "redirect_url": reverse("gerencia:listar_solicitudes_relevamiento")
                })
            except Exception as e:
                return JsonResponse({
                    "success": False,
                    "errors": {},
                    "message": f"Error al crear la solicitud: {str(e)}"
                }, status=500)
        else:
            return JsonResponse({
                "success": False,
                "errors": form.errors,
                "message": "Por favor corrija los errores en el formulario"
            })

    return JsonResponse({
        "success": False,
        "message": "Método no permitido"
    }, status=405)


def editar_solicitud_relevamiento(request, pk):
    """Editar solicitud (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, pk=pk)

    if not solicitud.puede_editar():
        return JsonResponse({
            'success': False,
            'message': 'Esta solicitud ya no puede ser editada'
        }, status=403)

    if request.method == "POST":
        # Usar el formulario de EDICIÓN (solo observaciones)
        form = EditarSolicitudRelevamientoForm(
            request.POST, instance=solicitud)
        if form.is_valid():
            form.save()

            # Guardar mensaje para toast en sesión
            request.session['toast_message'] = {
                'text': f'Solicitud de {solicitud.colonia.nombre} actualizada.',
                'type': 'info'
            }

            return JsonResponse({
                'success': True,
                'message': 'Solicitud actualizada exitosamente',
                'redirect_url': reverse("gerencia:listar_solicitudes_relevamiento")
            })
        else:
            # Agregar logging para ver qué errores hay
            print(f"Errores del formulario: {form.errors}")
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'message': 'Por favor corrija los errores en el formulario'
            })

    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    }, status=405)


def eliminar_solicitud_relevamiento(request, pk):
    """Eliminar solicitud (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, pk=pk)

    if not hasattr(solicitud, 'puede_borrar') or not solicitud.puede_borrar():
        return JsonResponse({
            'success': False,
            'message': 'Esta solicitud ya no puede ser eliminada'
        }, status=403)

    if request.method == "POST":
        try:
            solicitud_id = solicitud.id
            solicitud_colonia = solicitud.colonia.nombre
            solicitud.delete()

            # Guardar mensaje para toast en sesión
            request.session['toast_message'] = {
                'text': f'{solicitud_colonia}: La solicitud de Relevamiento fue eliminada.',
                'type': 'info'
            }

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al eliminar: {str(e)}'
            }, status=500)

    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    }, status=405)


def api_info_colonia(request, colonia_id):
    """API para obtener información de una colonia (AJAX)"""
    colonia = get_object_or_404(Colonia, pk=colonia_id)

    data = {
        'id': colonia.id,
        'nombre': colonia.nombre,
        'codigo': colonia.codigo,
        'tiene_relevamiento': colonia.tiene_relevamiento if hasattr(colonia, 'tiene_relevamiento') else False,
        'estado': colonia.estado,
        'distritos': [{
            'id': d.id,
            'nombre': d.nombre,
            'departamento': d.departamento.nombre
        } for d in colonia.distritos.all()[:3]]  # Primeros 3 distritos

    }

    return JsonResponse(data)
