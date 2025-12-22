from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from core.models import Departamento, Distrito, Colonia
from core.forms import ColoniaForm, DistritoForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.contrib.auth.models import User, Permission
from administrador.models import Rol
from gerencia.models import SolicitudRelevamiento
from gerencia.forms import SolicitudRelevamientoForm



# MUESTRA LA VISTA DEL ADMINISTRADOR
class GerenciaView(LoginRequiredMixin, TemplateView):
    template_name = 'gerencia/gerente_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['permisos'] = Permission.objects.all()  # Para el modal de creación de roles

        # Agregamos los QuerySets para que el template pueda contar
        context['departamentos'] = Departamento.objects.all()
        context['distritos'] = Distrito.objects.all()
        context['colonias'] = Colonia.objects.all()
        
       # context['objetivos'] = Objetivo.objects.all()
        #context['solicitudes'] = Solicitud.objects.all()
        #context['relevamientos'] = Relevamiento.objects.all()

        return context

# LISTA TODAS LAS SOLICITUDES (sin parámetro)
def lista_solicitudes_relevamiento(request):
    solicitudes = SolicitudRelevamiento.objects.select_related("colonia", "creado_por").all()
    return render(request, "includes/gerencia/tablas/lista_solicitud_relevamiento.html", {"solicitudes": solicitudes})

# OBTENER DATOS DE UNA SOLICITUD PARA EDITAR (con parámetro pk)
def obtener_datos_solicitud(request, pk):
    """Obtener datos de solicitud para editar (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, pk=pk)
    if not solicitud.puede_editar():
        return JsonResponse({'error': 'No se puede editar esta solicitud'}, status=403)
    
    data = {
        'success': True,
        
        'colonia': {
            'nombre': solicitud.colonia.nombre,
            'codigo': solicitud.colonia.codigo
        },
        'estado_display': solicitud.get_estado_display(),
        'observaciones': solicitud.observaciones
    }
    return JsonResponse(data)

def crear_solicitud_relevamiento(request, colonia_id):
    colonia = get_object_or_404(Colonia, pk=colonia_id)
    
    if request.method == "POST":
        form = SolicitudRelevamientoForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.colonia = colonia
            solicitud.creado_por = request.user
            solicitud.save()
            return JsonResponse({"success": True, "message": "Solicitud creada exitosamente"})
        else:
            return JsonResponse({"success": False, "errors": form.errors})
    # Si es GET, devolver error
    return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)

def editar_solicitud_relevamiento(request, pk):
    """Editar solicitud (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, pk=pk)
    
    if not solicitud.puede_editar():
        return JsonResponse({'error': 'Esta solicitud ya no puede ser editada'}, status=403)
    
    if request.method == "POST":
        form = SolicitudRelevamientoForm(request.POST, instance=solicitud)
        if form.is_valid():
            form.save() 
            return JsonResponse({
                'success': True, 
                'message': 'Solicitud actualizada exitosamente'
            })
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def eliminar_solicitud_relevamiento(request, pk):
    """Eliminar solicitud (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, pk=pk)
    
    # Verificar si se puede eliminar
    # Primero agregar método puede_borrar al modelo si no existe
    if not hasattr(solicitud, 'puede_borrar') or not solicitud.puede_borrar():
        return JsonResponse({'error': 'Esta solicitud ya no puede ser eliminada'}, status=403)
    
    if request.method == "POST":
        try:
            solicitud.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)