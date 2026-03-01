import os
from urllib import request
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, FileResponse
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.template.loader import render_to_string
from gerencia.models import SolicitudRelevamiento, SolicitudRelevamientoAudit
from gerencia.utils import procesar_auditorias
from django.db.models import Q
from .decorators import requiere_ser_digitalizador
from .froms import PrecatSubirForm
from .models import PrecatArchivo
from administrador.models import User
from django.db import models

# digitalizador/views.py


@login_required
@requiere_ser_digitalizador
def digitalizador_dashboard(request):
    """
    Dashboard para técnicos digitalizadores
    """
    # Obtener tareas donde el usuario es el digitalizador asignado
    tareas = SolicitudRelevamiento.objects.filter(
        Q(asignaciones_digitalizador__usuario_asignado=request.user) | Q(
            usuario_asignado=request.user)
    ).filter(
        # Solo mostrar tareas que están en el flujo SIG
        estado__in=[
            'asignado_a_digitalizador',
            'en_proceso_digitalizacion',
            'pendiente_revision_sig',
            'pendiente_aprobacion_campo',
            'aprobado_para_campo'
        ]
    ).select_related(
        'colonia', 'grupo_asignado', 'creado_por', 'grupo_asignado__lider'
    ).prefetch_related(
        'precat_archivos'
    ).order_by('-fecha_modificacion')

    # OBTENER TAREAS ASIGNADAS A COORDINACIÓN QUE FUERON DIGITALIZADAS POR EL USUARIO
    # Esto muestra las tareas que el usuario digitalizó y que ahora están en coordinación
    tareas_coordinacion = SolicitudRelevamiento.objects.filter(
        Q(asignaciones_digitalizador__usuario_asignado=request.user) | Q(
            usuario_asignado=request.user)
    ).filter(
        estado='asignado_coordinacion',
        fecha_aprobacion_campo__isnull=False
    ).select_related(
        'colonia', 'grupo_asignado', 'creado_por', 'grupo_asignado__lider'
    ).prefetch_related(
        'precat_archivos'
    ).order_by('-fecha_modificacion')

    # Estadísticas por estado
    estadisticas = {
        'pendientes': tareas.filter(estado='asignado_a_digitalizador').count(),
        'en_proceso': tareas.filter(estado='en_proceso_digitalizacion').count(),
        'pendientes_revision': tareas.filter(estado='pendiente_revision_sig').count(),
        'pendientes_aprobacion': tareas.filter(estado='pendiente_aprobacion_campo').count(),
        'aprobadas_campo': tareas.filter(estado='aprobado_para_campo').count(),
        'en_coordinacion': tareas_coordinacion.count(),  # Nueva estadística
        'total': tareas.count() + tareas_coordinacion.count(),
    }

    tareas_pendientes = tareas.filter(estado='asignado_a_digitalizador')
    tareas_en_proceso = tareas.filter(estado='en_proceso_digitalizacion')
    tareas_pendientes_revision = tareas.filter(estado='pendiente_revision_sig')
    tareas_pendientes_aprobacion = tareas.filter(
        estado='pendiente_aprobacion_campo')
    tareas_aprobadas_campo = tareas.filter(estado='aprobado_para_campo')

    # Contexto actualizado
    context = {
        'estadisticas': estadisticas,
        'tareas_pendientes': tareas_pendientes,
        'tareas_en_proceso': tareas_en_proceso,
        'tareas_pendientes_revision': tareas_pendientes_revision,
        'tareas_pendientes_aprobacion': tareas_pendientes_aprobacion,
        'tareas_aprobadas_campo': tareas_aprobadas_campo,
        'tareas_coordinacion': tareas_coordinacion,  # Nuevo: tareas en coordinación
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
        SolicitudRelevamiento.objects.select_related(
            'colonia', 'creado_por', 'grupo_asignado'
        ).prefetch_related('precat_archivos'),
        Q(asignaciones_digitalizador__usuario_asignado=request.user) | Q(
            usuario_asignado=request.user),
        pk=tarea_id
    )

    # Obtener archivos ya subidos
    archivos_precat = tarea.precat_archivos.filter(
        tipo_archivo=PrecatArchivo.TIPO_PRECAT).last()
    archivos_planos = tarea.precat_archivos.filter(
        tipo_archivo=PrecatArchivo.TIPO_PLANOS).last()

    # Obtener y procesar auditorías
    auditorias_raw = tarea.auditorias.all().select_related('cambiado_por')[:10]
    auditorias_procesadas = procesar_auditorias(auditorias_raw)

    context = {
        'tarea': tarea,
        'archivos_precat': archivos_precat,
        'archivos_planos': archivos_planos,
        'auditorias': auditorias_procesadas,
        'puede_iniciar': tarea.estado == 'asignado_a_digitalizador',
        'puede_subir': tarea.estado == 'en_proceso_digitalizacion',
        'puede_ver': tarea.estado in ['pendiente_revision_sig', 'pendiente_aprobacion_campo', 'aprobado_para_campo'],
    }

    return render(request, 'includes/digitalizador/detalle_tarea.html', context)


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
        Q(asignaciones_digitalizador__usuario_asignado=request.user) | Q(
            usuario_asignado=request.user),
        pk=tarea_id
    )

    if tarea.estado != 'asignado_a_digitalizador':
        return JsonResponse({
            'success': False,
            'message': 'La tarea no está en estado "Asignado a Digitalizador"'
        }, status=400)

    try:
        with transaction.atomic():
            # Marcar para evitar auditoría duplicada
            tarea._auditoria_creada = True
            tarea._cambiado_por = request.user

            # Cambiar estado
            tarea.estado = 'en_proceso_digitalizacion'
            tarea.fecha_inicio_etapa = timezone.now()
            tarea.save()

            # Registrar auditoría
            SolicitudRelevamientoAudit.objects.create(
                solicitud=tarea,
                campo='estado',
                valor_anterior='asignado_a_digitalizador',
                valor_nuevo='en_proceso_digitalizacion',
                cambiado_por=request.user,
                comentario=f'Digitalización iniciada por {request.user.get_full_name()}'
            )

            redirect_url = reverse(
                'digitalizador:detalle_tarea', args=[tarea_id])

            return JsonResponse({
                'success': True,
                'message': 'Digitalización iniciada',
                'estado': tarea.get_estado_display(),
                'redirect_url': redirect_url
            })
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()

        return JsonResponse({
            'success': False,
            'message': f'Error al iniciar digitalización: {str(e)}',
            'traceback': error_traceback
        }, status=500)


@login_required
@requiere_ser_digitalizador
def subir_precat(request, tarea_id):
    """
    Subir archivos de Precat y Planos, y cambiar estado a Pendiente de Revisión
    """
    tarea = get_object_or_404(
        SolicitudRelevamiento,
        pk=tarea_id,
        asignaciones_digitalizador__usuario_asignado=request.user
    )

    if tarea.estado != 'en_proceso_digitalizacion':
        messages.error(
            request,
            f'No puede subir archivos en el estado actual: {tarea.get_estado_display()}'
        )
        return redirect('digitalizador:detalle_tarea', tarea_id=tarea_id)

    if request.method == 'POST':
        form = PrecatSubirForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Guardar archivo Precat
                    archivo_precat = PrecatArchivo(
                        solicitud=tarea,
                        tipo_archivo=PrecatArchivo.TIPO_PRECAT,
                        archivo=form.cleaned_data['archivo_precat'],
                        observaciones=form.cleaned_data['observaciones'],
                        subido_por=request.user,
                        lotes_digitalizados=form.cleaned_data.get('lotes_digitalizados'),
                        calles=form.cleaned_data.get('calles'),
                        reservas=form.cleaned_data.get('reservas'),
                        campos_comunales=form.cleaned_data.get('campos_comunales'),
                        hectareas_aprox=form.cleaned_data.get('hectareas_aprox'),
                        metros_aprox=form.cleaned_data.get('metros_aprox')
                    )
                    archivo_precat.save()

                    # Guardar archivo Planos
                    archivo_planos = PrecatArchivo(
                        solicitud=tarea,
                        tipo_archivo=PrecatArchivo.TIPO_PLANOS,
                        archivo=form.cleaned_data['archivo_planos'],
                        observaciones=form.cleaned_data['observaciones'],
                        subido_por=request.user,
                        lotes_digitalizados=form.cleaned_data.get('lotes_digitalizados'),
                        calles=form.cleaned_data.get('calles'),
                        reservas=form.cleaned_data.get('reservas'),
                        campos_comunales=form.cleaned_data.get('campos_comunales'),
                        hectareas_aprox=form.cleaned_data.get('hectareas_aprox'),
                        metros_aprox=form.cleaned_data.get('metros_aprox')
                    )
                    archivo_planos.save()

                    # Cambiar estado de la solicitud
                    estado_anterior = tarea.estado
                    tarea.estado = 'pendiente_revision_sig'
                    tarea.observaciones = form.cleaned_data['observaciones']
                    tarea.save()

                    # Registrar auditoría
                    SolicitudRelevamientoAudit.objects.create(
                        solicitud=tarea,
                        campo='estado',
                        valor_anterior=estado_anterior,
                        valor_nuevo=tarea.estado,
                        cambiado_por=request.user,
                        comentario=f'Precat subido por {request.user.get_full_name()}. Archivos: {archivo_precat.get_nombre_archivo()}, {archivo_planos.get_nombre_archivo()}'
                    )

                    messages.success(
                        request,
                        'Archivos subidos correctamente. La solicitud está ahora pendiente de revisión por el Líder SIG.'
                    )
                    return redirect('digitalizador:digitalizador_dashboard')

            except Exception as e:
                messages.error(
                    request,
                    f'Error al subir archivos: {str(e)}'
                )
    else:
        form = PrecatSubirForm()

    context = {
        'tarea': tarea,
        'form': form,
    }

    return render(request, 'includes/digitalizador/subir_precat.html', context)


@login_required
@requiere_ser_digitalizador
def descargar_precat(request, archivo_id):
    """Descargar archivo Precat con autenticación"""
    archivo = get_object_or_404(PrecatArchivo, pk=archivo_id)

    # Verificar permisos: solo el digitalizador que subió o líder SIG puede descargar
    puede_descargar = (
        archivo.subido_por == request.user or
        request.user.grupos_pertenece.filter(
            nombre__icontains='SIG',
            lider=request.user
        ).exists() or
        archivo.solicitud.asignaciones_digitalizador.filter(usuario_asignado=request.user).exists()
    )

    if not puede_descargar:
        return HttpResponseForbidden("No tiene permisos para descargar este archivo")

    if not archivo.archivo_existe:
        messages.error(request, "El archivo no existe en el servidor")
        return redirect('digitalizador:detalle_tarea', tarea_id=archivo.solicitud.id)

    response = FileResponse(
        archivo.archivo.open('rb'),
        content_type='application/octet-stream'
    )
    response['Content-Disposition'] = f'attachment; filename="{archivo.get_nombre_archivo()}"'
    return response


@login_required
@requiere_ser_digitalizador
def listar_archivos_digitalizador(request):
    """
    Listar archivos subidos por el digitalizador actual
    """
    # Obtener archivos subidos por el usuario O donde es digitalizador
    archivos_precat = PrecatArchivo.objects.filter(
        models.Q(subido_por=request.user) |
        models.Q(solicitud__asignaciones_digitalizador__usuario_asignado=request.user)
    ).select_related(
        'solicitud',
        'solicitud__colonia'
    ).order_by('-fecha_subida')

    # Estadísticas
    estadisticas = {
        'total': archivos_precat.count(),
        'precat': archivos_precat.filter(tipo_archivo=PrecatArchivo.TIPO_PRECAT).count(),
        'planos': archivos_precat.filter(tipo_archivo=PrecatArchivo.TIPO_PLANOS).count(),
        'tamanio_total_mb': sum(a.get_tamanio_mb() for a in archivos_precat),
    }

    context = {
        'archivos': archivos_precat,
        'estadisticas': estadisticas,
        'usuario': request.user,
    }

    return render(request, 'digitalizador/archivos_precat.html', context)


@login_required
@requiere_ser_digitalizador
def descargar_archivo_digitalizador(request, archivo_id):
    """
    Descargar archivo Precat (para digitalizador)
    """
    archivo = get_object_or_404(PrecatArchivo, pk=archivo_id)

    # Verificar permisos: solo el que subió o líder SIG puede descargar
    puede_descargar = (
        archivo.subido_por == request.user or
        request.user.groups.filter(name__icontains='SIG_LIDER').exists()
    )

    if not puede_descargar:
        messages.error(
            request, "No tiene permisos para descargar este archivo.")
        return redirect('digitalizador:digitalizador_dashboard')

    # Verificar que el archivo existe
    if not archivo.archivo_existe:
        messages.error(request, "El archivo no existe en el servidor.")
        return redirect('digitalizador:listar_archivos_digitalizador')

    try:
        response = FileResponse(
            archivo.archivo.open('rb'),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{archivo.get_nombre_archivo()}"'
        return response
    except Exception as e:
        messages.error(request, f"Error al descargar el archivo: {str(e)}")
        return redirect('digitalizador:listar_archivos_digitalizador')
