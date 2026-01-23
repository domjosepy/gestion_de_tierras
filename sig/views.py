from django.shortcuts import render
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q, Count, Avg
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from gerencia.models import SolicitudRelevamiento, SolicitudRelevamientoAudit
from administrador.models import User
from sig.decorators import requiere_ser_sig, requiere_ser_lider_sig
from django.template.loader import render_to_string
from django.db import transaction


@login_required
@requiere_ser_sig
def sig_dashboard(request):
    """
    Dashboard optimizado para usuarios del grupo SIG
    """
    grupos_usuario = request.user.grupos_pertenece.filter(
        nombre__icontains='SIG',
        activo=True
    )

    if not grupos_usuario.exists():
        messages.warning(request, "No pertenece a ningún grupo SIG activo.")
        return render(request, 'sig/sig_dashboard.html', {
            'estadisticas': {},
            'es_lider': False
        })

    # Verificar si es líder
    es_lider = grupos_usuario.filter(lider=request.user).exists()

    # Base de consulta
    query = SolicitudRelevamiento.objects.filter(
        grupo_asignado__in=grupos_usuario
    ).select_related(
        'colonia', 'creado_por', 'grupo_asignado', 'usuario_asignado'
    ).prefetch_related(
        'colonia__distritos__departamento'
    )

    # Obtener solicitudes por estado
    solicitudes_pendientes = query.filter(estado='pendiente_asignacion_sig')
    solicitudes_asignadas = query.filter(estado='asignado_a_digitalizador')
    solicitudes_proceso = query.filter(estado='en_proceso_digitalizacion')
    solicitudes_revision = query.filter(estado='pendiente_revision_sig')
    solicitudes_analisis = query.filter(estado='pendiente_asignacion_analista')
    solicitudes_rechazadas = query.filter(estado='rechazado')
    solicitudes_finalizadas = query.filter(estado='finalizado')

    # Si no es líder, filtrar según corresponda
    if not es_lider:
        solicitudes_asignadas = solicitudes_asignadas.filter(
            usuario_asignado=request.user)
        solicitudes_proceso = solicitudes_proceso.filter(
            usuario_asignado=request.user)

    # Estadísticas
    estadisticas = {
        'total': query.count(),
        'pendiente_asignacion_sig': solicitudes_pendientes.count(),
        'asignado_a_digitalizador': solicitudes_asignadas.count(),
        'en_proceso_digitalizacion': solicitudes_proceso.count(),
        'pendiente_revision_sig': solicitudes_revision.count(),
        'pendiente_asignacion_analista': solicitudes_analisis.count(),
        'rechazado': solicitudes_rechazadas.count(),
        'finalizado': solicitudes_finalizadas.count(),
    }

    # Usuarios del grupo para asignación (solo líderes)
    usuarios_grupo = []
    if es_lider and grupos_usuario.exists():
        grupo_principal = grupos_usuario.first()
        usuarios_grupo = grupo_principal.usuarios.filter(
            estado='ACTIVO',
            is_active=True
        ).order_by('username')

    context = {
        'es_lider': es_lider,
        'grupos_usuario': grupos_usuario,
        'estadisticas': estadisticas,
        'usuarios_grupo': usuarios_grupo,
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_asignadas': solicitudes_asignadas,
        'solicitudes_proceso': solicitudes_proceso,
        'solicitudes_revision': solicitudes_revision,
        'solicitudes_analisis': solicitudes_analisis,
        'solicitudes_rechazadas': solicitudes_rechazadas,
        'solicitudes_finalizadas': solicitudes_finalizadas,
    }

    # Calcular urgencias para cada estado
    def contar_urgentes(queryset):
        return sum(1 for s in queryset if s.es_urgente())

    urgentes_pendientes = contar_urgentes(solicitudes_pendientes)
    urgentes_asignadas = contar_urgentes(solicitudes_asignadas)
    urgentes_proceso = contar_urgentes(solicitudes_proceso)
    # ... y así para cada estado ...

    context = {
        'es_lider': es_lider,
        'grupos_usuario': grupos_usuario,
        'estadisticas': estadisticas,
        'usuarios_grupo': usuarios_grupo,
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_asignadas': solicitudes_asignadas,
        'solicitudes_proceso': solicitudes_proceso,
        'solicitudes_revision': solicitudes_revision,
        'solicitudes_analisis': solicitudes_analisis,
        'solicitudes_rechazadas': solicitudes_rechazadas,
        'solicitudes_finalizadas': solicitudes_finalizadas,
        'urgentes_pendientes': urgentes_pendientes,
        'urgentes_asignadas': urgentes_asignadas,
        'urgentes_proceso': urgentes_proceso,
        'urgentes_revision': contar_urgentes(solicitudes_revision),
        'urgentes_analisis': contar_urgentes(solicitudes_analisis),
    }

    return render(request, 'sig/sig_dashboard.html', context)


@login_required
@requiere_ser_sig
def detalle_solicitud(request, solicitud_id):
    """
    Ver detalle completo de una solicitud
    """
    solicitud = get_object_or_404(
        SolicitudRelevamiento.objects.select_related(
            'colonia', 'creado_por', 'grupo_asignado', 'usuario_asignado', 'asignado_por'
        ),
        pk=solicitud_id
    )

    # Verificar que el usuario tenga acceso a esta solicitud
    grupos_usuario = request.user.grupos_pertenece.filter(
        nombre__icontains='SIG')
    if not (solicitud.grupo_asignado in grupos_usuario or
            solicitud.usuario_asignado == request.user or
            request.user.is_superuser):
        messages.error(request, "No tiene permisos para ver esta solicitud.")
        return redirect('sig:sig_dashboard')

    # Obtener información de la colonia
    distritos = solicitud.colonia.distritos.all()

    # Obtener auditorías
    auditorias = solicitud.auditorias.all().select_related('cambiado_por')

    # Verificar si puede asignar usuarios (si es líder del grupo)
    puede_asignar = False
    usuarios_disponibles = []

    if solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user:
        puede_asignar = True
        usuarios_disponibles = solicitud.grupo_asignado.usuarios.filter(
            estado='ACTIVO', is_active=True
        )

    context = {
        'solicitud': solicitud,
        'distritos': distritos,
        'auditorias': auditorias,
        'puede_asignar': puede_asignar,
        'usuarios_disponibles': usuarios_disponibles,
        'es_responsable': solicitud.usuario_asignado == request.user,
    }

    return render(request, 'sig/detalle_solicitud.html', context)


@login_required
@requiere_ser_lider_sig
def asignar_usuario_solicitud(request, solicitud_id):
    """Cambiar usuario asignado (solo para líderes del grupo)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)
    usuario_id = request.POST.get('usuario_id')
    comentario = request.POST.get('comentario', '')

    # Verificar que la solicitud esté en estado correcto
    if solicitud.estado != 'pendiente_asignacion_sig':
        return JsonResponse({
            'error': 'La solicitud no está en estado pendiente de asignación'
        }, status=400)

    # Verificar que el usuario sea líder del grupo asignado
    if not (solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user):
        return JsonResponse({
            'error': 'No es líder del grupo asignado'
        }, status=403)

    # Obtener usuario
    usuario = get_object_or_404(
        User, id=usuario_id, estado='ACTIVO', is_active=True)

    # Verificar que el usuario pertenece al grupo
    if usuario not in solicitud.grupo_asignado.usuarios.all():
        return JsonResponse({
            'error': 'El usuario no pertenece al grupo asignado'
        }, status=400)

    # SEGUNDO: Asignar TODOS los campos
    solicitud.usuario_asignado = usuario
    solicitud.asignado_por = request.user
    solicitud.fecha_asignacion = timezone.now()

    # TERCERO: Cambiar el estado
    solicitud.estado = 'asignado_a_digitalizador'

    # CUARTO: Guardar
    solicitud.save()

    return JsonResponse({
        'success': True,
        'message': f'Estudio de Relevamiento asignado a {usuario.username}'
    })


@login_required
@requiere_ser_lider_sig
def cambiar_usuario_solicitud(request, solicitud_id):
    """Cambiar usuario asignado (solo para líderes del grupo)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)
    usuario_id = request.POST.get('usuario_id')
    comentario = request.POST.get('comentario', '')

    # Verificar que la solicitud esté asignada
    if solicitud.estado != 'asignado_a_digitalizador':
        return JsonResponse({
            'error': 'La solicitud no está asignada'
        }, status=400)

    # Verificar que el usuario sea líder del grupo asignado
    if not (solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user):
        return JsonResponse({
            'error': 'No es líder del grupo asignado'
        }, status=403)

    # Obtener usuario
    usuario = get_object_or_404(
        User, id=usuario_id, estado='ACTIVO', is_active=True)

    # Verificar que el usuario pertenece al grupo
    if usuario not in solicitud.grupo_asignado.usuarios.all():
        return JsonResponse({
            'error': 'El usuario no pertenece al grupo asignado'
        }, status=400)

    # Guardar el usuario anterior para auditoría
    usuario_anterior = solicitud.usuario_asignado
    asignado_por_anterior = solicitud.asignado_por
    fecha_asignacion_anterior = solicitud.fecha_asignacion

    # Cambiar usuario
    solicitud.usuario_asignado = usuario
    solicitud.asignado_por = request.user
    solicitud.fecha_asignacion = timezone.now()
    solicitud.save()

    # Crear auditoría
    SolicitudRelevamientoAudit.objects.create(
        solicitud=solicitud,
        campo='usuario_asignado',
        valor_anterior=f"{usuario_anterior.username if usuario_anterior else 'Ninguno'} (Asignado por: {asignado_por_anterior.username if asignado_por_anterior else 'N/A'})",
        valor_nuevo=f"{usuario.username} (Asignado por: {request.user.username})",
        cambiado_por=request.user,
        comentario=comentario or f"Cambiado de {usuario_anterior.username if usuario_anterior else 'Ninguno'} a {usuario.username}"
    )

    return JsonResponse({
        'success': True,
        'message': f'Usuario cambiado a {usuario.username} correctamente'
    })


@login_required
@requiere_ser_lider_sig
def eliminar_asignacion(request, solicitud_id):
    """Eliminar asignación de usuario (solo para líderes del grupo)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)
    comentario = request.POST.get('comentario', '')

    # Validar que la solicitud esté en estado asignado
    if solicitud.estado != 'asignado_a_digitalizador':
        return JsonResponse({
            'error': 'La solicitud no está asignada a un digitalizador'
        }, status=400)

    # Verificar que el usuario sea líder del grupo asignado
    if not (solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user):
        return JsonResponse({
            'error': 'No es líder del grupo asignado'
        }, status=403)

    # Guardar información para auditoría
    usuario_anterior = solicitud.usuario_asignado
    asignado_por_anterior = solicitud.asignado_por

    # Eliminar asignación
    solicitud.usuario_asignado = None
    solicitud.asignado_por = None
    solicitud.fecha_asignacion = None
    solicitud.estado = 'pendiente_asignacion_sig'
    solicitud.save()

    # Crear auditoría
    SolicitudRelevamientoAudit.objects.create(
        solicitud=solicitud,
        campo='usuario_asignado',
        valor_anterior=f"{usuario_anterior.username if usuario_anterior else 'Ninguno'} (Asignado por: {asignado_por_anterior.username if asignado_por_anterior else 'N/A'})",
        valor_nuevo="Sin asignar",
        cambiado_por=request.user,
        comentario=comentario or f"Asignación eliminada por {request.user.username}"
    )

    return JsonResponse({
        'success': True,
        'message': 'Asignación eliminada correctamente'
    })


@login_required
@requiere_ser_sig
def obtener_estados_dashboard(request):
    """
    Obtener estadísticas y estados para el dashboard
    """
    grupos_usuario = request.user.grupos_pertenece.filter(
        nombre__icontains='SIG',
        activo=True
    )

    es_lider = grupos_usuario.filter(lider=request.user).exists()

    # Estados a mostrar
    estados_config = [
        {'key': 'pendiente_asignacion_sig', 'nombre': 'Pendientes de asignación'},
        {'key': 'asignado_a_digitalizador', 'nombre': 'Asignadas'},
        {'key': 'en_proceso_digitalizacion', 'nombre': 'En proceso'},
        {'key': 'pendiente_revision_sig', 'nombre': 'Pendientes de revisión'},
        {'key': 'pendiente_asignacion_analista', 'nombre': 'Enviadas a análisis'},
        {'key': 'rechazado', 'nombre': 'Rechazadas'},
        {'key': 'finalizado', 'nombre': 'Finalizadas'},
    ]

    query = SolicitudRelevamiento.objects.filter(
        grupo_asignado__in=grupos_usuario
    )

    # Calcular estadísticas
    estadisticas = {}
    estados_con_datos = []

    for estado in estados_config:
        qs = query.filter(estado=estado['key'])

        # Si no es líder, filtrar según corresponda
        if not es_lider and estado['key'] in ['asignado_a_digitalizador', 'en_proceso_digitalizacion']:
            qs = qs.filter(usuario_asignado=request.user)

        count = qs.count()
        estadisticas[estado['key']] = count

        if count > 0 or estado['key'] in ['pendiente_asignacion_sig', 'asignado_a_digitalizador']:
            estados_con_datos.append({
                'key': estado['key'],
                'nombre': estado['nombre'],
                'count': count
            })

    estadisticas['total'] = query.count()

    return JsonResponse({
        'success': True,
        'estadisticas': estadisticas,
        'estados': estados_con_datos,
        'es_lider': es_lider
    })


@login_required
@requiere_ser_sig
def cargar_tabla_estado(request, estado):
    """
    Cargar tabla de solicitudes para un estado específico
    """
    grupos_usuario = request.user.grupos_pertenece.filter(
        nombre__icontains='SIG',
        activo=True
    )

    es_lider = grupos_usuario.filter(lider=request.user).exists()

    # Base de consulta
    query = SolicitudRelevamiento.objects.filter(
        grupo_asignado__in=grupos_usuario,
        estado=estado
    ).select_related(
        'colonia', 'creado_por', 'grupo_asignado', 'usuario_asignado'
    ).prefetch_related(
        'colonia__distritos__departamento'
    )

    # Si no es líder, filtrar según estado
    if not es_lider and estado in ['asignado_a_digitalizador', 'en_proceso_digitalizacion']:
        query = query.filter(usuario_asignado=request.user)

    # Usuarios del grupo para asignación (solo líderes)
    usuarios_grupo = []
    if es_lider and estado in ['pendiente_asignacion_sig', 'asignado_a_digitalizador']:
        grupo_principal = grupos_usuario.first()
        usuarios_grupo = grupo_principal.usuarios.filter(
            estado='ACTIVO',
            is_active=True
        ).order_by('username')

    # Renderizar template
    html = render_to_string('includes/sig/tablas/tabla_estado.html', {
        'solicitudes': query,
        'estado': estado,
        'es_lider': es_lider,
        'usuarios_grupo': usuarios_grupo,
        'request': request
    })

    return JsonResponse({'html': html})


@login_required
@requiere_ser_sig
def iniciar_digitalizacion(request, solicitud_id):
    """
    Iniciar el proceso de digitalización (para el usuario asignado)
    """
    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)

    # Verificar que el usuario sea el asignado
    if solicitud.usuario_asignado != request.user:
        messages.error(request, "No está asignado a esta solicitud.")
        return redirect('sig:sig_dashboard')

    # Verificar estado
    if solicitud.estado != 'asignado_a_digitalizador':
        messages.error(
            request, "La solicitud no está lista para iniciar digitalización.")
        return redirect('sig:detalle_solicitud', solicitud_id=solicitud_id)

    # Cambiar estado
    solicitud.estado = 'en_proceso_digitalizacion'
    solicitud.save()

    messages.success(request, "Digitalización iniciada correctamente.")
    return redirect('sig:detalle_solicitud', solicitud_id=solicitud_id)


@login_required
@requiere_ser_sig
def finalizar_digitalizacion(request, solicitud_id):
    """
    Finalizar el proceso de digitalización (para el usuario asignado)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)

    # Verificar que el usuario sea el asignado
    if solicitud.usuario_asignado != request.user:
        return JsonResponse({
            'error': 'No está asignado a esta solicitud'
        }, status=403)

    # Verificar estado
    if solicitud.estado != 'en_proceso_digitalizacion':
        return JsonResponse({
            'error': 'La solicitud no está en proceso de digitalización'
        }, status=400)

    # Obtener observaciones del formulario
    observaciones = request.POST.get('observaciones', '')

    # Cambiar estado
    solicitud.estado = 'pendiente_revision_sig'
    solicitud.observaciones = observaciones
    solicitud.save()

    messages.success(
        request, "Digitalización finalizada. Pendiente de revisión.")

    return JsonResponse({
        'success': True,
        'message': 'Digitalización finalizada correctamente',
        'redirect_url': reverse('sig:detalle_solicitud', args=[solicitud_id])
    })


@login_required
@requiere_ser_lider_sig
def revisar_solicitud(request, solicitud_id):
    """
    Revisar una solicitud (para líderes)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)
    accion = request.POST.get('accion')  # 'aprobar' o 'rechazar'
    observaciones = request.POST.get('observaciones', '')

    # Verificar que el usuario sea líder del grupo
    if not (solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user):
        return JsonResponse({
            'error': 'No es líder del grupo asignado'
        }, status=403)

    # Verificar estado
    if solicitud.estado != 'pendiente_revision_sig':
        return JsonResponse({
            'error': 'La solicitud no está pendiente de revisión'
        }, status=400)

    # Procesar acción
    if accion == 'aprobar':
        solicitud.estado = 'pendiente_asignacion_analista'
        mensaje = "Solicitud aprobada. Pendiente de análisis."
    elif accion == 'rechazar':
        solicitud.estado = 'rechazado'
        solicitud.motivo_rechazo = observaciones
        mensaje = "Solicitud rechazada."
    else:
        return JsonResponse({'error': 'Acción no válida'}, status=400)

    solicitud.save()

    messages.success(request, mensaje)

    return JsonResponse({
        'success': True,
        'message': mensaje,
        'redirect_url': reverse('sig:sig_dashboard')
    })
