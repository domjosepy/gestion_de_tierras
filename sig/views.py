from django.shortcuts import render
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse
from django.template.loader import render_to_string
from django.db.models import Q, Count, Avg
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from administrador.models import User, Grupo
from gerencia.models import SolicitudRelevamiento, SolicitudRelevamientoAudit
from gerencia.utils import procesar_auditorias
from digitalizador.models import PrecatArchivo


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
    grupos_usuario = Grupo.objects.filter(
        (Q(usuarios__id=request.user.id) | Q(lider=request.user)),
        nombre__icontains='SIG',
        activo=True
    ).distinct()

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

    # Usuarios del grupo para contar solicitudes aprobadas/digitalizadas por el equipo
    usuarios_para_finalizadas = grupos_usuario.first().usuarios.all()

    # Contar finalizadas como aquellas con fecha de aprobación (por el grupo o por sus miembros)
    finalizadas_count = SolicitudRelevamiento.objects.filter(
        fecha_aprobacion_campo__isnull=False
    ).filter(
        Q(grupo_asignado__in=grupos_usuario) |
        Q(asignaciones_digitalizador__usuario_asignado__in=usuarios_para_finalizadas)
    ).distinct().count()

    # Estadísticas básicas

    estadisticas = {
        'total': query.count(),
        'pendientes': query.filter(estado='pendiente_asignacion_sig').count(),
        'en_proceso': query.filter(estado='en_proceso_digitalizacion').count(),
        'pendiente_revision': query.filter(estado='pendiente_revision_sig').count(),
        'rechazadas': query.filter(estado='rechazado').count(),
        'finalizadas': finalizadas_count,
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
    ).order_by('-fecha_creacion')
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
    grupos_usuario = Grupo.objects.filter(
        (Q(usuarios__id=request.user.id) | Q(lider=request.user)),
        nombre__icontains='SIG',
        activo=True
    ).distinct()

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

    # Mostrar las solicitudes aprobadas por fecha de aprobación (cualquier estado).
    # Además incluir solicitudes digitalizadas por miembros del grupo.
    usuarios_grupo = grupos_usuario.first().usuarios.all()
    query_aprobadas = SolicitudRelevamiento.objects.filter(
        fecha_aprobacion_campo__isnull=False
    ).filter(
        Q(grupo_asignado__in=grupos_usuario) |
        Q(asignaciones_digitalizador__usuario_asignado__in=usuarios_grupo)
    ).select_related(
        'colonia', 'creado_por', 'grupo_asignado', 'usuario_asignado'
    ).prefetch_related(
        'colonia__distritos__departamento'
    ).distinct()

    rechazadas_qs = SolicitudRelevamiento.objects.filter(estado='rechazado')
    try:
        miembros = grupos_usuario.first().usuarios.all()
        rechazadas_qs = rechazadas_qs.filter(
            Q(grupo_asignado__in=grupos_usuario) |
            Q(asignaciones_digitalizador__usuario_asignado__in=miembros)
        ).distinct()
    except Exception:
        rechazadas_qs = rechazadas_qs.filter(grupo_asignado__in=grupos_usuario)

    estados = {
        'pendientes': query.filter(estado='pendiente_asignacion_sig'),
        'asignadas': query.filter(estado='asignado_a_digitalizador'),
        'en_proceso': query.filter(estado='en_proceso_digitalizacion'),
        'pendiente_revision': query.filter(estado='pendiente_revision_sig'),
        'aprobadas': query_aprobadas,
        'rechazadas': rechazadas_qs,
        'finalizadas': query.filter(fecha_aprobacion_campo__isnull=False),
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

            # Calcular tiempos para la tabla de revisión (inicio/fin/elapsed)
            try:
                inicio = solicitud.fecha_inicio_etapa
                # si hay inicio y duración registrada, calcular fin
                if inicio and solicitud.tiempo_digitalizacion:
                    fin = inicio + solicitud.tiempo_digitalizacion
                else:
                    fin = None

                # elegir tiempo a mostrar: tiempo_digitalizacion si existe, sino tiempo en la etapa actual
                if solicitud.tiempo_digitalizacion:
                    tiempo_mostrar = solicitud.tiempo_digitalizacion
                else:
                    # llamar al método que devuelve tiempo en la etapa actual
                    try:
                        tiempo_mostrar = solicitud.obtener_tiempo_etapa_actual()
                    except Exception:
                        tiempo_mostrar = None

                solicitud.inicio_digitalizacion = inicio
                solicitud.fin_digitalizacion = fin
                solicitud.tiempo_digitalizacion_mostrar = tiempo_mostrar
            except Exception:
                solicitud.inicio_digitalizacion = None
                solicitud.fin_digitalizacion = None
                solicitud.tiempo_digitalizacion_mostrar = None

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
    # Verificar si el usuario es líder del grupo asignado (o superusuario)
    es_lider = False
    if solicitud.grupo_asignado and (solicitud.grupo_asignado.lider == request.user or request.user.is_superuser):
        es_lider = True

    # Verificar qué acciones puede realizar (solo para líderes)
    puede_asignar = False
    puede_cambiar = False
    puede_eliminar = False
    usuarios_grupo = []

    if solicitud.grupo_asignado and (solicitud.grupo_asignado.lider == request.user or request.user.is_superuser):
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

    # Añadir últimos archivos Precat/Planos al contexto para mostrar en el detalle
    try:
        ultimo_precat = solicitud.precat_archivos.filter(tipo_archivo=PrecatArchivo.TIPO_PRECAT).order_by('-fecha_subida').first()
    except Exception:
        ultimo_precat = None
    try:
        ultimo_planos = solicitud.precat_archivos.filter(tipo_archivo=PrecatArchivo.TIPO_PLANOS).order_by('-fecha_subida').first()
    except Exception:
        ultimo_planos = None

    context.update({
        'ultimo_precat': ultimo_precat,
        'ultimo_planos': ultimo_planos,
    })

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

    # Verificar que el usuario sea líder del grupo asignado (o superusuario)
    if not (solicitud.grupo_asignado and (solicitud.grupo_asignado.lider == request.user or request.user.is_superuser)):
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

        # Asignar usuario en la solicitud (usuario_asignado se mantiene) y guardar estado
        solicitud.usuario_asignado = usuario
        solicitud.asignado_por = request.user
        solicitud.fecha_asignacion = timezone.now()
        solicitud.estado = 'asignado_a_digitalizador'
        solicitud.save()

        # Registrar asignación en app `sig` (historial específico)
        try:
            from sig.models import AsignacionDigitalizador
            AsignacionDigitalizador.objects.create(
                solicitud=solicitud,
                registrado_por=request.user,
                usuario_asignado=usuario
            )
        except Exception:
            pass

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

    # Verificar que el usuario sea líder del grupo asignado (o superusuario)
    if not (solicitud.grupo_asignado and (solicitud.grupo_asignado.lider == request.user or request.user.is_superuser)):
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

    # Verificar que el usuario sea líder del grupo asignado (o superusuario)
    if not (solicitud.grupo_asignado and (solicitud.grupo_asignado.lider == request.user or request.user.is_superuser)):
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

    # Verificar que el usuario sea líder del grupo SIG (o superusuario)
    if not (solicitud.grupo_asignado and (solicitud.grupo_asignado.lider == request.user or request.user.is_superuser)):
        # Si la solicitud ya fue transferida a otro grupo, responder con éxito indicando el cambio
        return JsonResponse({
            'success': True,
            'message': 'La solicitud fue enviada a ' + solicitud.grupo_asignado.nombre + ' para su revisión.'
        })

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
                obs_text = f"APROBACIÓN SIG ({timestamp}) por {request.user.username}:\n{observacion}"

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
                valor_nuevo=solicitud.estado,
                cambiado_por=request.user,
                comentario=f'Aprobación SIG realizada por {request.user.username}. {observacion if observacion else "Sin observaciones"}'
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

    try:
        data = json.loads(request.body)
        motivo_rechazo = data.get('motivo_rechazo', '').strip()
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

    # Verificar que el usuario sea líder del grupo SIG (o superusuario)
    if not (solicitud.grupo_asignado and (solicitud.grupo_asignado.lider == request.user or request.user.is_superuser)):
        return JsonResponse({
            'success': False,
            'message': 'No tiene permisos para rechazar esta solicitud'
        }, status=403)

    # Validar estado
    estados_validos = ['en_proceso_digitalizacion', 'pendiente_revision_sig']
    if solicitud.estado not in estados_validos:
        return JsonResponse({
            'success': False,
            'message': f'La solicitud no está en un estado válido para rechazo. Estado actual: {solicitud.get_estado_display()}'
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

            # Evitar reasignación automática de grupo: mantener el grupo que realizó el rechazo
            solicitud._preservar_grupo = True

            # Agregar observaciones
            timestamp = timezone.now().strftime('%d/%m/%Y %H:%M')
            comentario_completo = f"Motivo rechazo: {motivo_rechazo}"
            obs_text = f"RECHAZO SIG ({timestamp}) por {request.user.username}:\n{comentario_completo}"

            if solicitud.observaciones:
                solicitud.observaciones += f"\n\n--- {obs_text}"
            else:
                solicitud.observaciones = f"--- {obs_text}"

            solicitud.save()

            # Registrar auditoría
            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='estado',
                valor_anterior=estado_anterior,
                valor_nuevo='rechazado',
                cambiado_por=request.user,
                comentario=f'Rechazo SIG realizado por {request.user.username}. {comentario_completo}'
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

    # Validar que hay observación
    if not observacion:
        return JsonResponse({
            'success': False,
            'message': 'Las observaciones son obligatorias para devolver una solicitud'
        }, status=400)

    # Definir transiciones válidas según estado origen
    transiciones = {
        'pendiente_revision_sig': 'en_proceso_digitalizacion',
        'asignado_coordinacion': 'asignado_a_digitalizador',
        'rechazado': 'asignado_a_digitalizador'
    }

    if solicitud.estado not in transiciones:
        return JsonResponse({
            'success': False,
            'message': f'No se puede devolver desde el estado actual: {solicitud.get_estado_display()}'
        }, status=400)

    try:
        with transaction.atomic():
            estado_anterior = solicitud.estado
            nuevo_estado = transiciones[estado_anterior]

            # Verificar que tiene usuario asignado
            if not solicitud.usuario_asignado:
                return JsonResponse({
                    'success': False,
                    'message': 'La solicitud no tiene un usuario asignado. No se puede devolver.'
                }, status=400)

            # Actualizar estado (SIN cambiar usuario_asignado)
            solicitud.estado = nuevo_estado

            # Solo si viene desde coordinación, reasignar grupo a SIG
            if estado_anterior == 'asignado_coordinacion':
                solicitud.fecha_aprobacion_campo = None
                from administrador.models import Grupo
                grupo_sig = Grupo.objects.filter(
                    nombre__icontains='SIG',
                    activo=True
                ).first()
                if grupo_sig:
                    solicitud.grupo_asignado = grupo_sig

            # Si viene desde rechazado, limpiar motivo de rechazo
            if estado_anterior == 'rechazado':
                solicitud.motivo_rechazo = ''

            # Agregar observaciones
            timestamp = timezone.now().strftime('%d/%m/%Y %H:%M')
            obs_text = f"CORRECCIÓN REQUERIDA ({timestamp}) por {request.user.username}:\n{observacion}"

            if solicitud.observaciones:
                solicitud.observaciones += f"\n\n--- {obs_text}"
            else:
                solicitud.observaciones = f"--- {obs_text}"

            solicitud.save()

            # Registrar auditoría
            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='estado',
                valor_anterior=estado_anterior,
                valor_nuevo=nuevo_estado,
                cambiado_por=request.user,
                comentario=f'Solicitud devuelta para corrección por {request.user.username}. Permanece asignada a {solicitud.usuario_asignado.username}. {observacion}'
            )

            # Mensaje personalizado según origen
            mensajes = {
                'pendiente_revision_sig': f'Solicitud devuelta a en proceso de digitalización. Asignada a {solicitud.usuario_asignado.username}.',
                'asignado_coordinacion': f'Solicitud devuelta desde Coordinación. Asignada a {solicitud.usuario_asignado.username}.',
                'rechazado': f'Solicitud devuelta a pendiente de revisión SIG. Asignada a {solicitud.usuario_asignado.username}.'
            }

            return JsonResponse({
                'success': True,
                'message': mensajes.get(estado_anterior, 'Solicitud devuelta correctamente.'),
                'estado': solicitud.get_estado_display(),
                'nuevo_estado': nuevo_estado,
                'usuario_asignado': solicitud.usuario_asignado.username
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al devolver para corrección: {str(e)}'
        }, status=500)
