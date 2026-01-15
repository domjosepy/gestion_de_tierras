
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from gerencia.models import SolicitudRelevamiento
from administrador.models import User
from sig.decorators import requiere_ser_sig, requiere_ser_lider_sig


@login_required
@requiere_ser_sig
def sig_dashboard(request):
    """
    Dashboard principal para usuarios del grupo SIG
    """
    # Depuración: mostrar grupos del usuario
    print(f"Usuario: {request.user.username}")
    print(
        f"Todos los grupos del usuario: {list(request.user.grupos_pertenece.all())}")

    # Obtener los grupos SIG del usuario
    grupos_usuario = request.user.grupos_pertenece.filter(
        nombre__icontains='SIG',
        activo=True
    )
    print(f"Grupos SIG activos del usuario: {list(grupos_usuario)}")
    print(f"Grupos SIG encontrados: {list(grupos_usuario)}")
    # Si no pertenece a ningún grupo SIG, mostrar mensaje
    if not grupos_usuario.exists():
        messages.warning(request, "No pertenece a ningún grupo SIG activo.")
        return render(request, 'sig/sig_dashboard.html', {
            'estadisticas': {},
            'solicitudes': []
        })

    # Filtrar solicitudes por los grupos del usuario y estado
    solicitudes = SolicitudRelevamiento.objects.filter(
        grupo_asignado__in=grupos_usuario
    ).select_related(
        'colonia',
        'creado_por',
        'grupo_asignado',
        'usuario_asignado'
    ).prefetch_related('colonia__distritos__departamento')

    print(f"Solicitudes encontradas: {solicitudes.count()}")

    # Depurar estados de solicitudes
    estados = solicitudes.values_list('estado', flat=True).distinct()
    print(f"Estados encontrados: {list(estados)}")

    # Estadísticas
    estadisticas = {
        'total': solicitudes.count(),
        'pendientes_asignacion': solicitudes.filter(
            estado='pendiente_asignacion_sig'
        ).count(),
        'asignadas_a_usuario': solicitudes.filter(
            estado='asignado_a_digitalizador',
            usuario_asignado=request.user
        ).count(),
        'en_proceso': solicitudes.filter(
            estado='en_proceso_digitalizacion',
            usuario_asignado=request.user
        ).count(),
        'pendientes_revision': solicitudes.filter(
            estado='pendiente_revision_sig'
        ).count(),
    }

    # Solicitudes por categoría
    solicitudes_pendientes = solicitudes.filter(
        estado='pendiente_asignacion_sig'
    )

    solicitudes_asignadas_a_mi = solicitudes.filter(
        estado='asignado_a_digitalizador',
        usuario_asignado=request.user
    )

    solicitudes_en_proceso_mi = solicitudes.filter(
        estado='en_proceso_digitalizacion',
        usuario_asignado=request.user
    )

    solicitudes_pendientes_revision = solicitudes.filter(
        estado='pendiente_revision_sig'
    )
    solicitudes_aprobadas = solicitudes.filter(
        estado='aprobado_para_campo'
    )
    solicitudes_rechazadas = solicitudes.filter(
        estado='rechazado'
    )

    # Si es líder, puede ver todas las solicitudes de su grupo
    es_lider = grupos_usuario.filter(lider=request.user).exists()

    if es_lider:
        solicitudes_asignadas_grupo = solicitudes.filter(
            estado='asignado_a_digitalizador'
        )
        solicitudes_en_proceso_grupo = solicitudes.filter(
            estado='en_proceso_digitalizacion'
        )
    else:
        solicitudes_asignadas_grupo = []
        solicitudes_en_proceso_grupo = []

    # Usuarios del grupo para asignación (solo para líderes)
    usuarios_grupo = []
    if es_lider and grupos_usuario.exists():
        # Tomar el primer grupo (o podrías hacer un selector)
        grupo_principal = grupos_usuario.first()
        usuarios_grupo = grupo_principal.usuarios.filter(
            estado='ACTIVO', is_active=True
        )

    context = {
        'estadisticas': estadisticas,
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_asignadas_a_mi': solicitudes_asignadas_a_mi,
        'solicitudes_asignadas_grupo': solicitudes_asignadas_grupo if es_lider else [],
        'solicitudes_en_proceso_mi': solicitudes_en_proceso_mi,
        'solicitudes_en_proceso_grupo': solicitudes_en_proceso_grupo if es_lider else [],
        'solicitudes_pendientes_revision': solicitudes_pendientes_revision,
        'solicitudes_aprobadas': solicitudes_aprobadas,
        'solicitudes_rechazadas': solicitudes_rechazadas,
        'usuarios_grupo': usuarios_grupo,
        'es_lider': es_lider,
        'grupos_usuario': grupos_usuario,
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
    """
    Asignar un usuario a una solicitud (solo para líderes del grupo)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)
    usuario_id = request.POST.get('usuario_id')

    # Validar que la solicitud esté en estado de asignación
    if solicitud.estado not in ['pendiente_asignacion_sig', 'asignado_a_digitalizador']:
        return JsonResponse({
            'error': 'La solicitud no está en estado para asignación'
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

    # Asignar usuario y actualizar estado
    solicitud.usuario_asignado = usuario
    solicitud.asignado_por = request.user

    # Si estaba pendiente, cambiar a asignado
    if solicitud.estado == 'pendiente_asignacion_sig':
        solicitud.estado = 'asignado_a_digitalizador'

    solicitud.save()

    messages.success(
        request, f"Usuario {usuario.username} asignado a la solicitud.")

    return JsonResponse({
        'success': True,
        'message': f'Usuario {usuario.username} asignado correctamente'
    })


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
