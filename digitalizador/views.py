# digitalizador/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from gerencia.models import SolicitudRelevamiento
from administrador.models import User
from .decorators import requiere_ser_digitalizador


@login_required
@requiere_ser_digitalizador
def digitalizador_dashboard(request):
    """
    Dashboard para técnicos digitalizadores
    """
    # Obtener tareas asignadas al usuario actual
    tareas = SolicitudRelevamiento.objects.filter(
        digitalizador_asignado=request.user
    ).select_related('colonia')

    # Estadísticas
    estadisticas = {
        'pendientes': tareas.filter(estado='asignado_a_digitalizador').count(),
        'en_proceso': tareas.filter(estado='en_proceso_digitalizacion').count(),
        'completadas': tareas.filter(estado='pendiente_revision_sig').count(),
        'total': tareas.count(),
    }

    # Tareas por estado
    tareas_pendientes = tareas.filter(estado='asignado_a_digitalizador')
    tareas_en_proceso = tareas.filter(estado='en_proceso_digitalizacion')

    context = {
        'estadisticas': estadisticas,
        'tareas_pendientes': tareas_pendientes,
        'tareas_en_proceso': tareas_en_proceso,
        'usuario': request.user,
    }

    return render(request, 'digitalizador/digitalizador_dashboard.html', context)


@login_required
@requiere_ser_digitalizador
def detalle_tarea(request, tarea_id):
    """
    Detalle de una tarea específica para digitalización
    """
    tarea = get_object_or_404(
        SolicitudRelevamiento.objects.select_related('colonia', 'creado_por'),
        pk=tarea_id,
        digitalizador_asignado=request.user  # Solo sus tareas
    )

    # Información de la colonia
    distritos = tarea.colonia.distritos.all()

    context = {
        'tarea': tarea,
        'distritos': distritos,
        'puede_iniciar': tarea.estado == 'asignado_a_digitalizador',
        'puede_finalizar': tarea.estado == 'en_proceso_digitalizacion',
    }

    return render(request, 'digitalizador/detalle_tarea.html', context)


@login_required
@requiere_ser_digitalizador
def iniciar_digitalizacion(request, tarea_id):
    """
    Marcar una tarea como en proceso de digitalización
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    tarea = get_object_or_404(
        SolicitudRelevamiento,
        pk=tarea_id,
        digitalizador_asignado=request.user
    )

    if not tarea.puede_iniciar_digitalizacion():
        return JsonResponse({
            'success': False,
            'message': 'No se puede iniciar esta tarea'
        })

    tarea.estado = 'en_proceso_digitalizacion'
    tarea.save()

    return JsonResponse({
        'success': True,
        'message': 'Digitalización iniciada',
        'estado': tarea.get_estado_display()
    })


@login_required
@requiere_ser_digitalizador
def finalizar_digitalizacion(request, tarea_id):
    """
    Marcar una tarea como finalizada (pendiente de revisión)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    tarea = get_object_or_404(
        SolicitudRelevamiento,
        pk=tarea_id,
        digitalizador_asignado=request.user
    )

    if not tarea.puede_finalizar_digitalizacion():
        return JsonResponse({
            'success': False,
            'message': 'No se puede finalizar esta tarea'
        })

    tarea.estado = 'pendiente_revision_sig'
    tarea.save()

    return JsonResponse({
        'success': True,
        'message': 'Digitalización finalizada, pendiente de revisión',
        'estado': tarea.get_estado_display()
    })
