from django.shortcuts import render
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, HttpResponseForbidden
from django.template.loader import render_to_string
from django.db.models import Q, Count, Avg
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from administrador.models import User
from gerencia.models import SolicitudRelevamiento, SolicitudRelevamientoAudit
from gerencia.signals import crear_auditoria_despues_guardar
from gerencia.utils import procesar_auditorias
from digitalizador.models import PrecatArchivo
from django.db.models.signals import post_save


from sig.decorators import requiere_ser_sig, requiere_ser_lider_sig
from django.template.loader import render_to_string
from django.db import transaction
# importar libreria json
import json

# ------------------ Dashboard y Listado de Solicitudes ------------------ #


@login_required
@requiere_ser_sig
def sig_dashboard(request):
    """
    Dashboard para usuarios del grupo SIG
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

    # Base de consulta para estadísticas
    query = SolicitudRelevamiento.objects.filter(
        grupo_asignado__in=grupos_usuario
    )

    # Estadísticas básicas
    estadisticas = {
        'pendientes': query.filter(estado='pendiente_asignacion_sig').count(),
        'asignadas': query.filter(estado='asignado_a_digitalizador').count(),
        'en_proceso': query.filter(estado='en_proceso_digitalizacion').count(),
        'pendiente_revision': query.filter(estado='pendiente_revision_sig').count(),
        'rechazadas': query.filter(estado='rechazado').count(),
        'finalizadas': query.filter(estado='finalizado').count(),
        'total': query.count(),

    }

    # Si es líder, mostrar usuarios del grupo
    usuarios_grupo = []
    if es_lider and grupos_usuario.exists():
        grupo_principal = grupos_usuario.first()
        usuarios_grupo = grupo_principal.usuarios.filter(
            estado='ACTIVO',
            is_active=True
        ).order_by('username').values('id', 'username', 'first_name', 'last_name')

    # Últimas 5 solicitudes para vista rápida
    ultimas_solicitudes = query.select_related(
        'colonia', 'creado_por', 'grupo_asignado', 'usuario_asignado'
    ).order_by('-fecha_creacion')[:5]

    context = {
        'es_lider': es_lider,
        'grupos_usuario': grupos_usuario,
        'estadisticas': estadisticas,
        'usuarios_grupo': usuarios_grupo,
        'ultimas_solicitudes': ultimas_solicitudes,
    }

    return render(request, 'sig/sig_dashboard.html', context)


@login_required
@requiere_ser_sig
def sig_solicitudes(request):
    """
    Vista COMPLETA de solicitudes para usuarios SIG
    """
    grupos_usuario = request.user.grupos_pertenece.filter(
        nombre__icontains='SIG',
        activo=True
    )

    if not grupos_usuario.exists():
        messages.warning(request, "No pertenece a ningún grupo SIG activo.")
        return render(request, 'includes/sig/tablas/solicitudes_relevamiento_sig.html', {
            'estadisticas': {},
            'es_lider': False
        })

    # Verificar si es líder
    es_lider = grupos_usuario.filter(lider=request.user).exists()

    # Base de consulta optimizada
    query = SolicitudRelevamiento.objects.filter(
        grupo_asignado__in=grupos_usuario
    ).select_related(
        'colonia', 'creado_por', 'grupo_asignado', 'usuario_asignado'
    ).prefetch_related(
        'colonia__distritos__departamento'
    )

    # PARA MOSTRAR SOLICITUDES ASIGNADAS AL GRUPO DE COORDINACION.
    query_aprobadas = SolicitudRelevamiento.objects.filter(
        # Digitalizadas por alguien del grupo SIG
        Q(usuario_digitalizador__in=grupos_usuario.first().usuarios.all()) |
        Q(estado='asignado_coordinacion', fecha_aprobacion_campo__isnull=False)
    ).filter(
        estado='asignado_coordinacion',
        fecha_aprobacion_campo__isnull=False
    ).select_related(
        'colonia', 'creado_por', 'grupo_asignado', 'usuario_asignado', 'usuario_digitalizador'
    ).prefetch_related(
        'colonia__distritos__departamento'
    )

    # Obtener solicitudes por estado
    estados = {
        'pendientes': query.filter(estado='pendiente_asignacion_sig'),
        'asignadas': query.filter(estado='asignado_a_digitalizador'),
        'en_proceso': query.filter(estado='en_proceso_digitalizacion'),
        'pendiente_revision': query.filter(estado='pendiente_revision_sig'),
        'aprobadas': query_aprobadas,
        'rechazadas': query.filter(estado='rechazado'),
        'finalizadas': query.filter(estado='finalizado'),
    }

    # Agregar propiedades para controlar botones
    for estado_key, solicitudes_qs in estados.items():
        for solicitud in solicitudes_qs:
            # Determinar si se puede asignar
            solicitud.puede_asignar_lider = (
                es_lider and
                solicitud.estado in ['pendiente_asignacion_sig', 'rechazado']
            )

            # Determinar si se puede cambiar asignación
            solicitud.puede_cambiar_asignacion = (
                es_lider and
                solicitud.estado == 'asignado_a_digitalizador'
            )

            # Determinar si se puede eliminar asignación
            solicitud.puede_eliminar_asignacion = (
                es_lider and
                solicitud.estado == 'asignado_a_digitalizador'
            )

            # Determinar acciones de revisión disponibles
            if es_lider:
                if solicitud.estado == 'en_proceso_digitalizacion':
                    solicitud.acciones_revision = [
                        'aprobar_revision', 'devolver_correccion', 'rechazar_revision']
                elif solicitud.estado == 'pendiente_revision_sig':
                    solicitud.acciones_revision = [
                        'aprobar_revision', 'rechazar_revision']
                else:
                    solicitud.acciones_revision = []

    # Si no es líder, filtrar según corresponda
    if not es_lider:
        estados['asignadas'] = estados['asignadas'].filter(
            usuario_asignado=request.user
        )
        estados['en_proceso'] = estados['en_proceso'].filter(
            usuario_asignado=request.user
        )

    # Estadísticas
    estadisticas = {key: qs.count() for key, qs in estados.items()}
    estadisticas['total'] = query.count()

    # Usuarios del grupo para asignación (solo líderes)
    usuarios_grupo = []
    if es_lider and grupos_usuario.exists():
        grupo_principal = grupos_usuario.first()
        usuarios_grupo = grupo_principal.usuarios.filter(
            estado='ACTIVO',
            is_active=True
        ).order_by('username')

    # Calcular urgencias
    urgentes = {key: sum(1 for s in qs if s.es_urgente())
                for key, qs in estados.items()}

    context = {
        'es_lider': es_lider,
        'grupos_usuario': grupos_usuario,
        'estadisticas': estadisticas,
        'usuarios_grupo': usuarios_grupo,
        'solicitudes_pendientes': estados['pendientes'],
        'solicitudes_asignadas': estados['asignadas'],
        'solicitudes_en_proceso': estados['en_proceso'],
        'solicitudes_revision': estados['pendiente_revision'],
        'solicitudes_aprobadas': estados['aprobadas'],
        'solicitudes_rechazadas': estados['rechazadas'],
        'solicitudes_finalizadas': estados['finalizadas'],
        'urgentes': urgentes,
    }

    return render(request, 'includes/sig/tablas/solicitudes_relevamiento_sig.html', context)

# ------------------ Detalle y Gestión de Solicitudes ------------------ #


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
    departamentos = [d.departamento for d in distritos]

    # Obtener y procesar auditorías
    auditorias_raw = solicitud.auditorias.all().select_related(
        'cambiado_por').order_by('-fecha')
    auditorias_procesadas = procesar_auditorias(auditorias_raw)
    # Verificar si el usuario es líder del grupo asignado
    es_lider = False
    if solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user:
        es_lider = True

    # Verificar qué acciones puede realizar (solo para líderes)
    puede_asignar = False
    puede_cambiar = False
    puede_eliminar = False
    usuarios_grupo = []

    if solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user:
        # Solo puede asignar en pendientes y rechazadas
        puede_asignar = solicitud.estado in [
            'pendiente_asignacion_sig', 'rechazado']

        # Solo puede cambiar en asignadas
        puede_cambiar = solicitud.estado == 'asignado_a_digitalizador'

        # Solo puede eliminar en asignadas
        puede_eliminar = solicitud.estado == 'asignado_a_digitalizador'

        # Obtener usuarios del grupo
        usuarios_grupo = solicitud.grupo_asignado.usuarios.filter(
            estado='ACTIVO', is_active=True
        )

    context = {
        'solicitud': solicitud,
        'distritos': distritos,
        'departamentos': departamentos,
        'auditorias': auditorias_procesadas,
        'puede_asignar': puede_asignar,
        'puede_cambiar': puede_cambiar,
        'puede_eliminar': puede_eliminar,
        'es_lider': es_lider,
        'usuarios_grupo': usuarios_grupo,
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

    # CAMBIO: Leer JSON en lugar de POST
    try:
        import json
        data = json.loads(request.body)
        usuario_id = data.get('usuario_id')
        comentario = data.get('comentario', '')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)

    # Validar que la solicitud esté en estados permitidos
    estados_permitidos = ['pendiente_asignacion_sig', 'rechazado']
    if solicitud.estado not in estados_permitidos:
        return JsonResponse({
            'error': 'Solo se pueden asignar solicitudes en estados: Pendiente de asignación o Rechazado'
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

    # Guardar el estado anterior para auditoría
    estado_anterior = solicitud.estado
    usuario_anterior = solicitud.usuario_asignado

    try:
        # Marcar que se creará auditoría manual (para evitar duplicación en signals)
        solicitud._auditoria_creada = True
        solicitud._cambiado_por = request.user

        # Asignar TODOS los campos
        solicitud.usuario_digitalizador = usuario
        solicitud.usuario_asignado = usuario
        solicitud.asignado_por = request.user
        solicitud.fecha_asignacion = timezone.now()
        # Cambiar el estado
        solicitud.estado = 'asignado_a_digitalizador'
        # Guardar
        solicitud.save()

        # Crear UN SOLO registro de auditoría combinado
        SolicitudRelevamientoAudit.objects.create(
            solicitud=solicitud,
            campo='asignacion_completa',
            valor_anterior=f"Estado: {estado_anterior}, Usuario: {usuario_anterior.username if usuario_anterior else 'Ninguno'}",
            valor_nuevo=f"Estado: asignado_a_digitalizador, Usuario: {usuario.username} (Asignado por: {request.user.username})",
            cambiado_por=request.user,
            comentario=comentario or f"Asignación completa realizada por {request.user.username}"
        )

    except Exception as e:
        return JsonResponse({
            'error': f'Error al asignar usuario: {str(e)}'
        }, status=500)

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

    # Validar que la solicitud esté en estado permitido
    if solicitud.estado != 'asignado_a_digitalizador':
        return JsonResponse({
            'error': 'Solo se puede cambiar el digitalizador en estado "Asignado a digitalizador"'
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
        comentario=comentario or f"Cambio realizado por {request.user.username}: de {usuario_anterior.username if usuario_anterior else 'Ninguno'} a {usuario.username}"
    )

    return JsonResponse({
        'success': True,
        'message': f'Usuario cambiado a {usuario.username}.'
    })


@login_required
@requiere_ser_lider_sig
def eliminar_asignacion(request, solicitud_id):
    """Eliminar asignación de usuario (solo para líderes del grupo)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)
    comentario = request.POST.get('comentario', '')

    # Validar que la solicitud esté en estado permitido
    if solicitud.estado != 'asignado_a_digitalizador':
        return JsonResponse({
            'error': 'Solo se puede eliminar asignación en estado "Asignado a digitalizador"'
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


# ------------------ Gestión de Archivos Precat ------------------ #


@login_required
@requiere_ser_sig
def listar_archivos_precat(request):
    """
    Listar todos los archivos Precat disponibles para el grupo SIG
    """
    grupos_usuario = request.user.grupos_pertenece.filter(
        nombre__icontains='SIG',
        activo=True
    )

    if not grupos_usuario.exists():
        messages.warning(request, "No pertenece a ningún grupo SIG activo.")
        return render(request, 'sig/archivos_precat.html', {'archivos': []})

    # Obtener solicitudes del grupo
    solicitudes_grupo = SolicitudRelevamiento.objects.filter(
        grupo_asignado__in=grupos_usuario
    )

    # Obtener archivos Precat de esas solicitudes
    archivos_precat = PrecatArchivo.objects.filter(
        solicitud__in=solicitudes_grupo
    ).select_related(
        'solicitud',
        'solicitud__colonia',
        'subido_por'
    ).order_by('-fecha_subida')

    # Estadísticas
    estadisticas = {
        'total': archivos_precat.count(),
        'precat': archivos_precat.filter(tipo_archivo=PrecatArchivo.TIPO_PRECAT).count(),
        'planos': archivos_precat.filter(tipo_archivo=PrecatArchivo.TIPO_PLANOS).count(),
    }

    context = {
        'archivos': archivos_precat,
        'estadisticas': estadisticas,
        'grupos_usuario': grupos_usuario,
    }

    return render(request, 'sig/archivos_precat.html', context)


@login_required
@requiere_ser_sig
def descargar_archivo_precat(request, archivo_id):
    """
    Descargar archivo Precat (para usuarios SIG)
    """
    archivo = get_object_or_404(PrecatArchivo, pk=archivo_id)

    # Verificar permisos: usuario debe pertenecer al mismo grupo SIG
    grupos_usuario = request.user.grupos_pertenece.filter(
        nombre__icontains='SIG',
        activo=True
    )

    if archivo.solicitud.grupo_asignado not in grupos_usuario:
        messages.error(
            request, "No tiene permisos para descargar este archivo.")
        return redirect('sig:sig_dashboard')

    # Verificar que el archivo existe
    if not archivo.archivo_existe:
        messages.error(request, "El archivo no existe en el servidor.")
        return redirect('sig:listar_archivos_precat')

    try:
        response = FileResponse(
            archivo.archivo.open('rb'),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{archivo.get_nombre_archivo()}"'
        return response
    except Exception as e:
        messages.error(request, f"Error al descargar el archivo: {str(e)}")
        return redirect('sig:listar_archivos_precat')


@login_required
@requiere_ser_sig
def obtener_archivos_solicitud(request, solicitud_id):
    """
    Obtener archivos de una solicitud específica (para modal)
    """
    solicitud = get_object_or_404(SolicitudRelevamiento, pk=solicitud_id)

    # Verificar permisos
    grupos_usuario = request.user.grupos_pertenece.filter(
        nombre__icontains='SIG',
        activo=True
    )

    if solicitud.grupo_asignado not in grupos_usuario:
        return JsonResponse({'error': 'No tiene permisos'}, status=403)

    # Obtener archivos
    archivos_precat = solicitud.precat_archivos.filter(
        tipo_archivo=PrecatArchivo.TIPO_PRECAT
    )
    archivos_planos = solicitud.precat_archivos.filter(
        tipo_archivo=PrecatArchivo.TIPO_PLANOS
    )

    # Renderizar template
    html = render_to_string('includes/sig/modal/archivos_precat_lista.html', {
        'archivos_precat': archivos_precat,
        'archivos_planos': archivos_planos,
        'solicitud': solicitud,
    })

    return JsonResponse({'html': html})


# ------------------ Vistas para Aprobar y Rechazar Digitalización Devolver para correccion ------------------ #

@login_required
@requiere_ser_lider_sig
def aprobar_digitalizacion(request, solicitud_id):
    """
    Aprobar digitalización (para líderes SIG)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        observacion = data.get('observacion', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Datos JSON inválidos'
        }, status=400)

    solicitud = get_object_or_404(
        SolicitudRelevamiento.objects.select_related(
            'colonia', 'grupo_asignado', 'usuario_asignado'
        ),
        pk=solicitud_id
    )

    # Verificar que el usuario sea líder del grupo SIG
    if not (solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user):
        return JsonResponse({
            'success': False,
            'message': 'No tiene permisos para aprobar esta solicitud'
        }, status=403)

    # Validar estado
    estados_validos = ['en_proceso_digitalizacion', 'pendiente_revision_sig']
    if solicitud.estado not in estados_validos:
        return JsonResponse({
            'success': False,
            'message': f'La solicitud no está en un estado válido para aprobación. Estado actual: {solicitud.get_estado_display()}'
        }, status=400)

    try:
        with transaction.atomic():
            estado_anterior = solicitud.estado
            nuevo_estado = None
            mensaje = ""

            # Determinar el nuevo estado según el estado actual
            if solicitud.estado == 'en_proceso_digitalizacion':
                # Aprobar digitalización, pasar a revisión SIG
                nuevo_estado = 'pendiente_revision_sig'
                mensaje = 'Digitalización aprobada. Pendiente de revisión SIG.'

            elif solicitud.estado == 'pendiente_revision_sig':
                # Aprobar revisión SIG según tipo de solicitud
                if solicitud.tipo == 'relevamiento':
                    # Para RELEVAMIENTOS: aprobado_para_campo (se auto-transiciona a asignado_coordinacion)
                    nuevo_estado = 'aprobado_para_campo'
                    mensaje = 'Revisión SIG aprobada. Aprobado para campo y asignado a coordinación.'

                    # Registrar fecha de aprobación para campo
                    solicitud.fecha_aprobacion_campo = timezone.now()

                else:  # actualizacion
                    # Para ACTUALIZACIONES: directo a análisis
                    nuevo_estado = 'pendiente_asignacion_analista'
                    mensaje = 'Revisión SIG aprobada. Pendiente de asignación a analista.'

            # Validar transición
            estados_siguientes = solicitud.obtener_estados_siguientes(
                request.user)
            if nuevo_estado not in estados_siguientes:
                return JsonResponse({
                    'success': False,
                    'message': f'Transición no permitida de {solicitud.get_estado_display()} a {dict(solicitud.ESTADOS).get(nuevo_estado)}'
                }, status=400)

            # Actualizar estado
            solicitud.estado = nuevo_estado
            solicitud.cambiado_por = request.user

            # Agregar observación si existe
            if observacion:
                timestamp = timezone.now().strftime('%d/%m/%Y %H:%M')
                obs_text = f"APROBACIÓN SIG ({timestamp}) por {request.user.get_full_name()}:\n{observacion}"

                if solicitud.observaciones:
                    solicitud.observaciones += f"\n\n--- {obs_text}"
                else:
                    solicitud.observaciones = f"--- {obs_text}"

            # Guardar (esto disparará la transición automática en el save del modelo)
            solicitud.save()

            # Registrar auditoría
            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='estado',
                valor_anterior=estado_anterior,
                valor_nuevo=solicitud.estado,  # Usar el estado final después del save
                cambiado_por=request.user,
                comentario=f'Aprobación SIG realizada por {request.user.get_full_name()}. {observacion if observacion else "Sin observaciones"}'
            )

            return JsonResponse({
                'success': True,
                'message': mensaje,
                'estado': solicitud.get_estado_display(),
                'nuevo_estado': solicitud.estado
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al aprobar la digitalización: {str(e)}'
        }, status=500)


@login_required
@requiere_ser_lider_sig
def rechazar_digitalizacion(request, solicitud_id):
    """
    Rechazar digitalización (para líderes SIG)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    data = json.loads(request.body)
    motivo_rechazo = data.get('motivo_rechazo', '').strip()
    observacion = data.get('observacion', '').strip()

    solicitud = get_object_or_404(
        SolicitudRelevamiento.objects.select_related(
            'colonia', 'grupo_asignado', 'usuario_asignado'
        ),
        pk=solicitud_id
    )

    # Verificar que el usuario sea líder del grupo SIG
    if not (solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user):
        return JsonResponse({
            'success': False,
            'message': 'No tiene permisos para rechazar esta solicitud'
        }, status=403)

    # Validar estado
    estados_validos = ['en_proceso_digitalizacion', 'pendiente_revision_sig']
    if solicitud.estado not in estados_validos:
        return JsonResponse({
            'success': False,
            'message': f'La solicitud no está en un estado válido para rechazo'
        }, status=400)

    # Validar motivo de rechazo (obligatorio)
    if not motivo_rechazo:
        return JsonResponse({
            'success': False,
            'message': 'El motivo del rechazo es obligatorio'
        }, status=400)

    try:
        with transaction.atomic():
            estado_anterior = solicitud.estado

            # Actualizar a estado rechazado
            solicitud.estado = 'rechazado'
            solicitud.motivo_rechazo = motivo_rechazo
            solicitud.cambiado_por = request.user

            # Agregar observaciones
            comentario_completo = f"Motivo rechazo: {motivo_rechazo}"
            if observacion:
                comentario_completo += f"\nObservaciones adicionales: {observacion}"

            if solicitud.observaciones:
                solicitud.observaciones += f"\n\n--- RECHAZO SIG ({timezone.now().strftime('%d/%m/%Y %H:%M')}) ---\n{comentario_completo}"
            else:
                solicitud.observaciones = f"--- RECHAZO SIG ({timezone.now().strftime('%d/%m/%Y %H:%M')}) ---\n{comentario_completo}"

            solicitud.save()

            # Registrar auditoría
            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='estado',
                valor_anterior=estado_anterior,
                valor_nuevo='rechazado',
                cambiado_por=request.user,
                comentario=f'Rechazo SIG realizado por {request.user.get_full_name()}. {comentario_completo}'
            )

            # También crear una auditoría específica para el motivo del rechazo
            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='motivo_rechazo',
                valor_anterior='',
                valor_nuevo=motivo_rechazo,
                cambiado_por=request.user,
                comentario='Motivo de rechazo registrado'
            )

            return JsonResponse({
                'success': True,
                'message': 'Digitalización rechazada correctamente.',
                'estado': solicitud.get_estado_display(),
                'nuevo_estado': 'rechazado'
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al rechazar la digitalización: {str(e)}'
        }, status=500)


@login_required
@requiere_ser_lider_sig
def devolver_para_correccion(request, solicitud_id):
    """
    Devolver digitalización para corrección (para líderes SIG)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        observacion = data.get('observacion', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Datos JSON inválidos'
        }, status=400)

    solicitud = get_object_or_404(
        SolicitudRelevamiento.objects.select_related(
            'colonia', 'grupo_asignado', 'usuario_asignado'
        ),
        pk=solicitud_id
    )

    # Verificar que el usuario sea líder del grupo SIG
    if not (solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user):
        return JsonResponse({
            'success': False,
            'message': 'No tiene permisos para devolver esta solicitud'
        }, status=403)

    # CAMBIO: Aceptar AMBOS estados
    estados_validos = ['en_proceso_digitalizacion', 'pendiente_revision_sig']
    if solicitud.estado not in estados_validos:
        return JsonResponse({
            'success': False,
            'message': f'Solo se pueden devolver solicitudes en proceso de digitalización o pendiente de revisión SIG. Estado actual: {solicitud.get_estado_display()}'
        }, status=400)

    # Validar que hay observación
    if not observacion:
        return JsonResponse({
            'success': False,
            'message': 'Las observaciones son obligatorias para devolver una solicitud'
        }, status=400)

    try:
        with transaction.atomic():
            estado_anterior = solicitud.estado

            # CAMBIO: Volver al estado "en_proceso_digitalizacion"
            solicitud.estado = 'en_proceso_digitalizacion'

            # Agregar observaciones
            if solicitud.observaciones:
                solicitud.observaciones += f"\n\n--- CORRECCIÓN REQUERIDA ({timezone.now().strftime('%d/%m/%Y %H:%M')}) ---\n{observacion}"
            else:
                solicitud.observaciones = f"--- CORRECCIÓN REQUERIDA ({timezone.now().strftime('%d/%m/%Y %H:%M')}) ---\n{observacion}"

            solicitud.save()

            # Registrar auditoría
            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='estado',
                valor_anterior=estado_anterior,
                valor_nuevo='en_proceso_digitalizacion',
                cambiado_por=request.user,
                comentario=f'Solicitud devuelta para corrección por {request.user.get_full_name()}. {observacion}'
            )

            return JsonResponse({
                'success': True,
                'message': 'Solicitud devuelta para corrección. El digitalizador ha sido notificado.',
                'estado': solicitud.get_estado_display()
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al devolver para corrección: {str(e)}'
        }, status=500)
