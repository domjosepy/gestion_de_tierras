from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.contrib import messages
from gerencia.models import SolicitudRelevamiento
from administrador.models import User
from sig.decorators import requiere_ser_sig


@login_required
@requiere_ser_sig
def sig_dashboard(request):
    """
    Dashboard principal para administradores SIG
    """
    # Estadísticas
    estadisticas = {
        'total': SolicitudRelevamiento.objects.count(),
        'pendientes_asignacion': SolicitudRelevamiento.objects.filter(
            estado='pendiente_asignacion_sig'
        ).count(),
        'asignadas': SolicitudRelevamiento.objects.filter(
            estado='asignado_a_digitalizador'
        ).count(),
        'en_proceso': SolicitudRelevamiento.objects.filter(
            estado='en_proceso_digitalizacion'
        ).count(),
        'pendientes_revision': SolicitudRelevamiento.objects.filter(
            estado='pendiente_revision_sig'
        ).count(),
        'aprobadas': SolicitudRelevamiento.objects.filter(
            estado='aprobada'
        ).count(),
        'rechazadas': SolicitudRelevamiento.objects.filter(
            estado='rechazada'
        ).count(),
    }

    # Solicitudes por estado
    solicitudes_pendientes = SolicitudRelevamiento.objects.filter(
        estado='pendiente_asignacion_sig'
    ).select_related('colonia', 'creado_por')

    solicitudes_asignadas = SolicitudRelevamiento.objects.filter(
        estado='asignado_a_digitalizador'
    ).select_related('colonia', 'digitalizador_asignado')

    solicitudes_en_proceso = SolicitudRelevamiento.objects.filter(
        estado='en_proceso_digitalizacion'
    ).select_related('colonia', 'digitalizador_asignado')

    solicitudes_pendientes_revision = SolicitudRelevamiento.objects.filter(
        estado='pendiente_revision_sig'
    ).select_related('colonia', 'digitalizador_asignado')

    solicitudes_aprobadas = SolicitudRelevamiento.objects.filter(
        estado='aprobada'
    ).select_related('colonia', 'digitalizador_asignado')

    solicitudes_rechazadas = SolicitudRelevamiento.objects.filter(
        estado='rechazada'
    ).select_related('colonia', 'digitalizador_asignado')

    # Digitalizadores disponibles
    digitalizadores = User.objects.filter(
        groups__name='Digitalizador')

    context = {
        'estadisticas': estadisticas,
        'solicitudes_pendientes': solicitudes_pendientes,
        'solicitudes_asignadas': solicitudes_asignadas,
        'solicitudes_en_proceso': solicitudes_en_proceso,
        'solicitudes_pendientes_revision': solicitudes_pendientes_revision,
        'solicitudes_aprobadas': solicitudes_aprobadas,
        'solicitudes_rechazadas': solicitudes_rechazadas,
        'digitalizadores': digitalizadores,
    }

    return render(request, 'sig/sig_dashboard.html', context)


@login_required
@requiere_ser_sig
def asignar_digitalizador(request, solicitud_id):
    """
    Asignar un digitalizador a una solicitud (AJAX)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    solicitud = get_object_or_404(SolicitudRelevamiento, pk=solicitud_id)
    digitalizador_id = request.POST.get('digitalizador_id')

    if not solicitud.puede_asignar_digitalizador():
        return JsonResponse({
            'success': False,
            'message': 'Esta solicitud no puede ser asignada en su estado actual'
        })

    try:
        digitalizador = User.objects.get(
            pk=digitalizador_id,
            groups__name='Digitalizador'
        )

        solicitud.digitalizador_asignado = digitalizador
        solicitud.estado = 'asignado_a_digitalizador'
        solicitud.save()

        # Agregar mensaje de éxito usando Django messages
        messages.success(
            request,
            f'Solicitud asignada correctamente a {digitalizador.get_full_name() or digitalizador.username}'
        )

        return JsonResponse({
            'success': True,
            'message': f'Asignado a {digitalizador.get_full_name()}',
            'digitalizador': {
                'id': digitalizador.id,
                'nombre': digitalizador.get_full_name() or digitalizador.username,
                'username': digitalizador.username,
            }
        })

    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Digitalizador no encontrado'
        })


@login_required
@requiere_ser_sig
def detalle_solicitud(request, solicitud_id):
    """
    Ver detalle completo de una solicitud
    """
    solicitud = get_object_or_404(
        SolicitudRelevamiento.objects.select_related(
            'colonia', 'creado_por', 'digitalizador_asignado'
        ),
        pk=solicitud_id
    )

    # Obtener información de la colonia
    distritos = solicitud.colonia.distritos.all()

    context = {
        'solicitud': solicitud,
        'distritos': distritos,
    }

    return render(request, 'sig/detalle_solicitud.html', context)
