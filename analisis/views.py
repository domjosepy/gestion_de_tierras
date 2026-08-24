from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.contrib import messages
from django.utils import timezone
from administrador.models import User, Grupo
from core.models import Colonia
from coordinacion.models import OrdenTrabajo
from digitalizador.models import PrecatArchivo
from gerencia.models import SolicitudRelevamiento, SolicitudRelevamientoAudit
from gerencia.utils import procesar_auditorias
from relevamiento.models import Relevamiento, ArchivoSubcoordinador


from analisis.decorators import requiere_ser_analisis, requiere_ser_lider_analisis
from analisis.models import AsignacionAnalista
from django.db import transaction
import json


# ------------------ Dashboard y Listado de Colonias Relevadas y Solicitudes ------------------ #

@login_required
@requiere_ser_lider_analisis
def analisis_dashboard(request):
    """
    Dashboard principal del módulo de Análisis. Solo accesible para líderes del grupo ANALISIS.

    Propósito y flujo de datos:
        1. Verifica que el usuario pertenezca a al menos un grupo ANALISIS activo.
        2. Obtiene las OrdenesTrabajo completadas (estado='completada', activa=False,
           tipo='relevamiento') como fuente canónica de colonias relevadas.
        3. Pre-agrega en Python tres diccionarios de conteo (encuestas, archivos precat,
           archivos subcoordinador) indexados por colonia/orden para evitar consultas N+1.
        4. Construye `colonias_dashboard`, una lista de dicts con una entrada por colonia
           (usando la OT más reciente), fusionando datos geográficos, coordinador y conteos.
        5. Calcula `estadisticas_colonias` (total, con_relevamiento, con/sin actualizaciones)
           a partir de un queryset adicional sobre `Colonia`.
        6. Calcula `estadisticas` de solicitudes (total, pendientes, en_proceso, etc.)
           filtrando por `grupo_asignado__in=grupos_usuario`.
        7. Si el usuario es líder, carga `usuarios_grupo` para el panel de asignación.

    Variables de contexto (template context):
        es_lider (bool): True si el usuario es líder de algún grupo ANALISIS activo.
        grupos_usuario (QuerySet[Grupo]): Grupos ANALISIS activos a los que pertenece el usuario.
        estadisticas (dict): Conteos de solicitudes por estado:
            - total, pendientes, en_proceso, pendiente_revision, rechazadas, finalizadas.
        usuarios_grupo (list[dict]): Usuarios activos del grupo (id, username, first_name,
            last_name). Solo presente cuando es_lider=True.
        ultimas_solicitudes (QuerySet[SolicitudRelevamiento]): Todas las solicitudes asignadas
            al grupo, ordenadas por fecha_creacion DESC. Sin límite de registros.
        colonias_relevadas (list[dict]): Una entrada por colonia relevada con:
            id, colonia_nombre, colonia_codigo, distrito_nombre, departamento_nombre,
            fecha_relevada, coordinador_campo, encuestas_total, total_archivos, tiene_relevamiento.
        estadisticas_colonias (dict): Conteos agregados de colonias:
            - total, con_relevamiento, con_actualizaciones, sin_actualizaciones.

    Lógica crítica:
        - La fuente canónica de colonias relevadas son las OT completadas, NO el estado
          de la SolicitudRelevamiento. Esto desacopla el progreso del relevamiento de campo
          del flujo de análisis.
        - El campo `colonia.tiene_relevamiento` y `conteo_actualizaciones` son flags
          desnormalizados en el modelo Colonia, actualizados por la señal `save()` de
          SolicitudRelevamiento al transicionar a estado 'finalizado'.
        - `finalizadas_count` usa `distinct()` sobre un OR con JOIN a M2M
          (`asignaciones_digitalizador__usuario_asignado__in`), lo que puede ser costoso
          en tablas grandes.

    Cuellos de botella (query efficiency):
        - ALTO: `ultimas_solicitudes` no tiene límite de registros (sin slice ni paginación).
          En producción con cientos de solicitudes, renderiza toda la tabla en memoria.
          Recomendación: agregar `[:50]` o implementar paginación AJAX.
        - MEDIO: `qs_stats = Colonia.objects.filter(id__in=seen_colonias)` genera un hit
          adicional a la BD después del loop solo para dos `.count()`. Puede eliminarse
          calculando `con_relevamiento` y `con_actualizaciones` directamente durante la
          construcción de `colonias_dashboard` (iterando la lista resultante en Python).
        - MEDIO: `finalizadas_count` usa `distinct()` con dos condiciones OR sobre FKs
          y M2M, lo que genera un DISTINCT costoso. Considerar dividir en dos queries
          separadas y sumar con `|` (union de sets de IDs).
        - BAJO: `colonia.distritos.first()` dentro del loop usa el prefetch de
          `solicitud__colonia__distritos__departamento`, pero `.first()` no garantiza
          el uso del caché prefetch en todas las versiones de Django. Verificar con
          Django Debug Toolbar.
    """
    grupos_usuario = Grupo.objects.filter(
        (Q(usuarios__id=request.user.id) | Q(lider=request.user)),
        nombre__icontains='ANALISIS',
        activo=True
    ).distinct()

    if not grupos_usuario.exists():
        messages.warning(request, "No pertenece a ningún grupo ANALISIS activo.")
        return render(request, 'analisis/analisis_dashboard.html', {
            'estadisticas': {},
            'es_lider': False
        })

    # Verificar si es líder
    es_lider = grupos_usuario.filter(lider=request.user).exists()

     # -------------------------------------------------------
    # Colonias relevadas: lista estructurada con datos de OT
    # (sin filtro de grupo; las OT se completan en el flujo
    #  de RELEVAMIENTO antes de llegar a ANALISIS)
    # -------------------------------------------------------
    ordenes_completadas = OrdenTrabajo.objects.filter(
        estado='completada',
        activa=False,
        solicitud__tipo='relevamiento',
    ).select_related(
        'solicitud__colonia',
        'coordinador_responsable',
    ).prefetch_related(
        'solicitud__colonia__distritos__departamento',
        'equipos_asignados__coordinador_campo',
    ).order_by('solicitud__colonia__nombre', '-fecha_creacion')

    # Pre-agregar conteos para evitar consultas N+1
    colonia_ids_completadas = list(
        ordenes_completadas.values_list('solicitud__colonia_id', flat=True).distinct()
    )

    encuestas_por_colonia = {
        item['colonia_id']: item['total']
        for item in Relevamiento.objects.filter(
            colonia_id__in=colonia_ids_completadas,
            orden_trabajo__estado='completada',
        ).values('colonia_id').annotate(total=Count('id'))
    } if colonia_ids_completadas else {}

    archivos_precat_por_colonia = {
        item['solicitud__colonia_id']: item['total']
        for item in PrecatArchivo.objects.filter(
            solicitud__colonia_id__in=colonia_ids_completadas,
        ).values('solicitud__colonia_id').annotate(total=Count('id'))
    } if colonia_ids_completadas else {}

    archivos_subcoor_por_orden = {
        item['orden_trabajo_id']: item['total']
        for item in ArchivoSubcoordinador.objects.filter(
            orden_trabajo__in=ordenes_completadas,
        ).values('orden_trabajo_id').annotate(total=Count('id'))
    }

    # Construir un registro por colonia usando la última OT completada
    seen_colonias = set()
    colonias_dashboard = []

    for orden in ordenes_completadas:
        sol = orden.solicitud
        if not sol or not sol.colonia:
            continue
        colonia = sol.colonia
        if colonia.id in seen_colonias:
            continue
        seen_colonias.add(colonia.id)

        distrito = colonia.distritos.first()
        departamento = distrito.departamento if distrito else None

        equipo = orden.equipos_asignados.first()
        if equipo and getattr(equipo, 'coordinador_campo', None):
            u = equipo.coordinador_campo
            coord_nombre = f"{u.first_name} {u.last_name}".strip() or u.username
        elif orden.coordinador_responsable:
            u = orden.coordinador_responsable
            coord_nombre = f"{u.first_name} {u.last_name}".strip() or u.username
        else:
            coord_nombre = 'Sin coordinador'

        colonias_dashboard.append({
            'id': sol.id,
            'colonia_nombre': colonia.nombre,
            'colonia_codigo': colonia.codigo,
            'distrito_nombre': distrito.nombre if distrito else 'Sin distrito',
            'departamento_nombre': departamento.nombre if departamento else 'Sin departamento',
            'fecha_relevada': orden.fecha_fin_real,
            'coordinador_campo': coord_nombre,
            'encuestas_total': encuestas_por_colonia.get(colonia.id, 0),
            'total_archivos': (
                archivos_precat_por_colonia.get(colonia.id, 0) +
                archivos_subcoor_por_orden.get(orden.id, 0)
            ),
            'tiene_relevamiento': colonia.tiene_relevamiento,
        })

    # Estadísticas para las tarjetas superiores
    if seen_colonias:
        qs_stats = Colonia.objects.filter(id__in=seen_colonias)
        estadisticas_colonias = {
            'total': len(colonias_dashboard),
            'con_relevamiento': qs_stats.filter(tiene_relevamiento=True).count(),
            'con_actualizaciones': qs_stats.filter(conteo_actualizaciones__gt=0).count(),
            'sin_actualizaciones': qs_stats.filter(conteo_actualizaciones=0).count(),
        }
    else:
        estadisticas_colonias = {
            'total': 0, 'con_relevamiento': 0,
            'con_actualizaciones': 0, 'sin_actualizaciones': 0,
        }

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
        'pendientes': query.filter(estado='pendiente_asignacion_analisis').count(),
        'en_proceso': query.filter(estado='en_proceso_analisis').count(),
        'pendiente_revision': query.filter(estado='pendiente_revision_analisis').count(),
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

    # Últimas solicitudes para vista rápida
    ultimas_solicitudes = query.select_related(
        'colonia', 'creado_por', 'grupo_asignado', 'usuario_asignado'
    ).order_by('-fecha_creacion')

    context = {
        'es_lider': es_lider,
        'grupos_usuario': grupos_usuario,
        'estadisticas': estadisticas,
        'usuarios_grupo': usuarios_grupo,
        'ultimas_solicitudes': ultimas_solicitudes,
        'colonias_relevadas': colonias_dashboard,
        'estadisticas_colonias': estadisticas_colonias,
    }

    return render(request, 'analisis/analisis_dashboard.html', context)


@login_required
@requiere_ser_analisis
def obtener_datos_relevamiento_analisis(request, pk):
    """
    Retorna los datos completos de un relevamiento finalizado para el modal de detalles
    del módulo de Análisis.

    Vista autónoma: construye su propia respuesta usando los métodos de negocio del
    modelo SolicitudRelevamiento (get_orden_trabajo_completada, get_estadisticas_relevamiento,
    get_info_analista) en lugar de delegar a la vista de Gerencia. Esto elimina el
    acoplamiento implícito y permite que cada módulo evolucione de forma independiente.

    Args:
        request (HttpRequest): GET autenticado con @requiere_ser_analisis.
        pk (int): PK de SolicitudRelevamiento.

    Returns:
        JsonResponse: {success: true, solicitud, orden_trabajo, colonia, distrito,
                       departamento, grupo_info, usuario_info, analista_info,
                       coordinador_campo_info, subcoordinadores_info,
                       encuestadores_info, estadisticas}
        JsonResponse con status 404 si no existe la solicitud o no tiene OT completada.
        JsonResponse con status 500 ante errores inesperados.
    """
    try:
        solicitud = get_object_or_404(SolicitudRelevamiento, pk=pk)

        orden_trabajo = solicitud.get_orden_trabajo_completada()
        if not orden_trabajo:
            return JsonResponse({
                'success': False,
                'error': 'No se encontró una orden de trabajo completada para esta solicitud',
            }, status=404)

        # Datos geográficos
        colonia = solicitud.colonia
        distrito = colonia.distritos.first() if colonia.distritos.exists() else None
        departamento = distrito.departamento if distrito else None

        # Información de asignación de grupo y usuario actual
        grupo_info = None
        if solicitud.grupo_asignado:
            grupo_info = {
                'nombre': solicitud.grupo_asignado.nombre,
                'lider': solicitud.grupo_asignado.lider.username if solicitud.grupo_asignado.lider else None,
                'color': solicitud.grupo_asignado.color or '#6c757d',
            }

        usuario_info = None
        if solicitud.usuario_asignado:
            u = solicitud.usuario_asignado
            usuario_info = {
                'username': u.username,
                'email': u.email,
                'nombre_completo': f"{u.first_name} {u.last_name}".strip() or u.username,
            }

        # Equipo de relevamiento
        digitalizador_info = None
        coordinador_campo_info = None
        subcoordinadores_info = []
        encuestadores_info = []

        # El digitalizador no pertenece a EquipoRelevamiento; se toma de la
        # asignación más reciente registrada para la solicitud.
        digitalizador = solicitud.usuario_digitalizador
        if digitalizador:
            digitalizador_info = {
                'username': digitalizador.username,
                'email': digitalizador.email,
                'nombre_completo': f"{digitalizador.first_name} {digitalizador.last_name}".strip() or digitalizador.username,
            }

        equipo = orden_trabajo.equipos_asignados.first()
        if equipo:
            if equipo.coordinador_campo:
                c = equipo.coordinador_campo
                coordinador_campo_info = {
                    'username': c.username,
                    'email': c.email,
                    'nombre_completo': f"{c.first_name} {c.last_name}".strip() or c.username,
                }
            for subcoor in equipo.subcoordinadores.all():
                subcoordinadores_info.append({
                    'username': subcoor.username,
                    'email': subcoor.email,
                    'nombre_completo': f"{subcoor.first_name} {subcoor.last_name}".strip() or subcoor.username,
                })
            for enc in equipo.encuestadores.all():
                encuestadores_info.append({
                    'username': enc.username,
                    'email': enc.email,
                    'nombre_completo': f"{enc.first_name} {enc.last_name}".strip() or enc.username,
                })

        # Información de analista — via método del modelo (import local internamente)
        analista_info = solicitud.get_info_analista()

        # Estadísticas — via método del modelo
        estadisticas = solicitud.get_estadisticas_relevamiento(orden_trabajo)

        fmt = lambda dt: timezone.localtime(dt).strftime("%d/%m/%Y %H:%M") if dt else None  

        data = {
            'success': True,
            'solicitud': {
                'id': solicitud.id,
                'tipo': solicitud.tipo,
                'tipo_display': solicitud.get_tipo_display(),
                'estado': solicitud.estado,
                'estado_display': solicitud.get_estado_display(),
                'fecha_creacion': fmt(solicitud.fecha_creacion),
                'fecha_aprobacion': fmt(solicitud.fecha_aprobacion_campo),
                'fecha_asignacion': fmt(solicitud.fecha_asignacion),
            },
            'orden_trabajo': {
                'id': orden_trabajo.id,
                'estado': orden_trabajo.estado,
                'estado_display': orden_trabajo.get_estado_display(),
                'fecha_creacion': fmt(orden_trabajo.fecha_creacion),
                'fecha_inicio_planeada': orden_trabajo.fecha_inicio_planeada.strftime("%d/%m/%Y") if orden_trabajo.fecha_inicio_planeada else None,
                'fecha_fin_planeada': orden_trabajo.fecha_fin_planeada.strftime("%d/%m/%Y") if orden_trabajo.fecha_fin_planeada else None,
                'fecha_inicio_real': orden_trabajo.fecha_inicio_real.strftime("%d/%m/%Y") if orden_trabajo.fecha_inicio_real else None,
                'fecha_fin_real': orden_trabajo.fecha_fin_real.strftime("%d/%m/%Y") if orden_trabajo.fecha_fin_real else None,
            },
            'colonia': {
                'nombre': colonia.nombre,
                'codigo': colonia.codigo,
            },
            'distrito': {
                'nombre': distrito.nombre,
                'codigo': distrito.codigo,
            },
            'departamento': {
                'nombre': departamento.nombre,
                'codigo': departamento.codigo,
            },
            'grupo_info': grupo_info,
            'usuario_info': usuario_info,
            'analista_info': analista_info,
            'digitalizador_info': digitalizador_info,
            'coordinador_campo_info': coordinador_campo_info,
            'subcoordinadores_info': subcoordinadores_info,
            'encuestadores_info': encuestadores_info,
            'estadisticas': estadisticas,
            'solicitudes_firmadas': estadisticas.get('solicitudes_firmadas', 0),
        }

        return JsonResponse(data)

    except SolicitudRelevamiento.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Solicitud no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error al obtener datos: {str(e)}'}, status=500)

# ------------------------------------ DETALLE DE ASIGNACIÓN DE RELEVAMIENTO ------------------ #

@login_required
@requiere_ser_analisis
def detalle_asignacion_relevamiento(request, solicitud_id):
    """Detalle de asignacion de colonia relevada para el modulo Analisis."""
    # Fuente canonica para Analisis: la colonia debe provenir de una OT completada.
    orden_trabajo = get_object_or_404(
        OrdenTrabajo.objects.select_related(
            'solicitud__colonia',
            'solicitud__creado_por',
            'solicitud__grupo_asignado',
            'solicitud__usuario_analista',
            'solicitud__usuario_asignado',
            'solicitud__ultima_asignacion_por',
        ).prefetch_related(
            'solicitud__colonia__distritos__departamento',
            'equipos_asignados__coordinador_campo',
        ),
        solicitud_id=solicitud_id,
        estado='completada',
        activa=False,
    )
    solicitud = orden_trabajo.solicitud

    # Validación de permisos: el usuario debe ser superusuario, 
    # líder del grupo asignado, o analista asignado a la solicitud.
    grupos_usuario = Grupo.objects.filter(
        Q(usuarios__id=request.user.id) | Q(lider=request.user),
        nombre__icontains='ANALISIS',
        activo=True,
    ).distinct()

    if not request.user.is_superuser:
        tiene_asignacion = AsignacionAnalista.objects.filter(
            # Verifica si el usuario tiene asignación activa de análisis para esta solicitud
            solicitud=solicitud,
            # Filtra por analista actual y estados que indican que la asignación está en curso o finalizada
            analista=request.user,
            # Solo considera asignaciones que estén en estado activo o finalizado, no canceladas
            estado__in=['analista_asignado', 'proceso_analisis', 'proceso_empate', 'analisis_finalizado'],
        ).exists()
        if not (grupos_usuario.exists() and (solicitud.grupo_asignado_id in grupos_usuario.values_list('id', flat=True) or tiene_asignacion)):
            messages.error(request, 'No tiene permisos para ver este detalle de analisis.')
            return redirect('analisis:colonias_relevadas_analisis')

    es_lider = request.user.is_superuser or grupos_usuario.filter(lider=request.user).exists()

    distritos = solicitud.colonia.distritos.select_related('departamento').all() if solicitud.colonia_id else []
    departamentos = [d.departamento for d in distritos if d.departamento]

    asignacion_actual = AsignacionAnalista.objects.filter(
        solicitud=solicitud,
    ).select_related('analista', 'lider_asignador').order_by('-fecha_asignacion').first()

    estadisticas_relevamiento = solicitud.get_estadisticas_relevamiento(orden_trabajo) if orden_trabajo else {}

    ultimo_precat = PrecatArchivo.objects.filter(
        solicitud=solicitud,
        tipo_archivo=PrecatArchivo.TIPO_PRECAT,
    ).order_by('-fecha_subida').first()
    ultimo_planos = PrecatArchivo.objects.filter(
        solicitud=solicitud,
        tipo_archivo=PrecatArchivo.TIPO_PLANOS,
    ).order_by('-fecha_subida').first()

    archivos_gis = ArchivoSubcoordinador.objects.none()
    
    if orden_trabajo:
        archivos_gis = ArchivoSubcoordinador.objects.filter(
            orden_trabajo=orden_trabajo,
        ).select_related('subido_por').order_by('-fecha_subida')[:5]

    auditorias_raw = solicitud.auditorias.all().select_related('cambiado_por').order_by('-fecha')
    auditorias = procesar_auditorias(auditorias_raw)

    manzanas_relevadas = []
    if orden_trabajo and solicitud.colonia_id:
        manzanas_relevadas = list(
            Relevamiento.objects.filter(
                orden_trabajo=orden_trabajo,
                colonia_id=solicitud.colonia_id,
            )
            .exclude(manzana__isnull=True)
            .exclude(manzana='')
            .values_list('manzana', flat=True)
            .distinct()
            .order_by('manzana')
        )

    usuarios_grupo = []
    if es_lider and grupos_usuario.exists():
        usuarios_grupo = grupos_usuario.first().usuarios.filter(
            estado='ACTIVO',
            is_active=True,
        ).exclude(id=request.user.id).order_by('username')

    antecedentes_pdf = getattr(solicitud, 'archivo_antecedentes', None)
    senatics_pdf = getattr(solicitud, 'archivo_senatics', None)

    context = {
        'solicitud': solicitud,
        'asignacion_actual': asignacion_actual,
        'distritos': distritos,
        'departamentos': departamentos,
        'auditorias': auditorias,
        'es_lider': es_lider,
        'usuarios_grupo': usuarios_grupo,
        'es_responsable': asignacion_actual.analista_id == request.user.id if asignacion_actual else False,
        'orden_trabajo': orden_trabajo,
        'estadisticas_relevamiento': estadisticas_relevamiento,
        'manzanas_relevadas': manzanas_relevadas,
        'ultimo_precat': ultimo_precat,
        'ultimo_planos': ultimo_planos,
        'archivos_gis': archivos_gis,
        # Si existen estos campos en el modelo, se renderizan; si no, quedan en None.
        'antecedentes_pdf': antecedentes_pdf,
        'senatics_pdf': senatics_pdf,
    }
    return render(request, 'analisis/detalle_asignacion_relevamiento.html', context)

# ------------------ Asignación de analista a colonia relevada (POST) ------------------ #
@login_required
@requiere_ser_lider_analisis
@require_POST
def relevamiento_asignar_analista(request, solicitud_id):
    """
    Asigna un analista a una colonia relevada con base en OT completada y finalizada.

    Reglas de negocio:
    1. Solo acepta POST (vía @require_POST).
    2. Solo líderes del grupo ANALISIS o superusuarios.
    3. El líder no puede asignarse a sí mismo.
    4. Valida JSON de entrada con `usuario_id` obligatorio y `comentario` opcional.
    5. La OT asociada a la solicitud debe existir y estar en estado
       `completada` con `activa=False`.
    6. Evita duplicados: si la OT/colonia ya tiene asignación activa de análisis,
       rechaza la operación.
    7. Registra auditoría en AsignacionAnalista con estado `analista_asignado`.

    Respuestas:
    - 200: asignación exitosa.
    - 400: JSON inválido, usuario fuera del grupo, OT no completada,
           o asignación activa existente.
    - 403: sin permisos de líder ANALISIS.
    - 404: solicitud/OT/usuario no encontrado.
    - 500: error interno al guardar.
    """
    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)

    try:
        data = json.loads(request.body)
        usuario_id = data.get('usuario_id')
        comentario = data.get('comentario', '')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)

    if not usuario_id:
        return JsonResponse({'error': 'El campo usuario_id es obligatorio'}, status=400)

    # El líder debe pertenecer a un grupo ANALISIS activo (o ser superusuario)
    if not request.user.is_superuser:
        grupo_analisis = Grupo.objects.filter(
            lider=request.user,
            nombre__icontains='ANALISIS',
            activo=True
        ).first()
        if not grupo_analisis:
            return JsonResponse({'error': 'No es líder de ningún grupo ANALISIS activo'}, status=403)
    else:
        grupo_analisis = Grupo.objects.filter(
            nombre__icontains='ANALISIS', activo=True
        ).first()

    if not grupo_analisis:
        return JsonResponse({'error': 'No tiene permisos de líder ANALISIS'}, status=403)

    usuario = get_object_or_404(User, id=usuario_id, estado='ACTIVO', is_active=True)

    if usuario not in grupo_analisis.usuarios.all():
        return JsonResponse({'error': 'El usuario no pertenece al grupo ANALISIS'}, status=400)

    if usuario == request.user:
        return JsonResponse({'error': 'No puede asignarse a sí mismo'}, status=400)

    # Obtener OT más reciente asociada a la solicitud (contexto de asignación)
    orden_ot = solicitud.ordenes_trabajo.order_by('-fecha_creacion').first()
    if not orden_ot:
        return JsonResponse({'error': 'Orden de Trabajo no encontrada'}, status=404)

    if orden_ot.estado != 'completada' or orden_ot.activa:
        return JsonResponse({'error': 'La Orden de Trabajo no está completada/finalizada'}, status=400)

    estados_activos = ['analista_asignado', 'proceso_analisis', 'proceso_empate']
    ya_asignada = AsignacionAnalista.objects.filter(
        Q(orden_trabajo=orden_ot) | Q(solicitud__colonia_id=solicitud.colonia_id),
        estado__in=estados_activos,
    ).exists()

    if ya_asignada:
        return JsonResponse({'error': 'La OT/colonia ya tiene una asignación activa'}, status=400)

    try:
        with transaction.atomic():
            AsignacionAnalista.objects.create(
                solicitud=solicitud,
                orden_trabajo=orden_ot,
                analista=usuario,
                lider_asignador=request.user,
                estado='analista_asignado',
                observaciones=comentario,
            )

            # Mantener consistencia de estado y responsable en la solicitud.
            solicitud.usuario_analista = usuario
            solicitud.usuario_asignado = usuario
            solicitud.ultima_asignacion_por = request.user
            solicitud.fecha_asignacion = timezone.now()
            solicitud.estado = 'asignado_a_analista'
            solicitud.save(update_fields=[
                'usuario_analista',
                'usuario_asignado',
                'ultima_asignacion_por',
                'fecha_asignacion',
                'estado',
            ])

            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='usuario_analista',
                valor_anterior='Sin asignar',
                valor_nuevo=f"{usuario.username} (asignado por: {request.user.username})",
                cambiado_por=request.user,
                comentario=comentario or f"Asignacion de analista realizada por {request.user.username}",
            )

    except Exception as e:
        return JsonResponse({'error': f'Error al asignar analista: {str(e)}'}, status=500)

    return JsonResponse({
        'success': True,
        'message': 'Analista asignado correctamente.'
    })


@login_required
@requiere_ser_lider_analisis
def cambiar_analista_asignacion(request, asignacion_id):
    """
    Reemplaza el analista de una AsignacionAnalista activa (solo POST, solo líderes).

    Propósito y flujo de datos:
        Implementa el patrón "cancelar + crear nuevo" para mantener historial completo:
        1. Obtiene la asignación activa (`estado__in=['analista_asignado', 'proceso_analisis']`) con
           la solicitud asociada.
        2. Resuelve el grupo ANALISIS del líder.
        3. Valida al nuevo analista (activo, en el grupo, no es el líder mismo).
        4. Dentro de `transaction.atomic()`:
           a. Marca la asignación actual como 'cancelado' con `fecha_termino=now()`.
           b. Crea una nueva `AsignacionAnalista` con el nuevo analista.
           c. Actualiza los campos de asignación en la solicitud.
           d. Registra en `SolicitudRelevamientoAudit`.

    Args:
        request (HttpRequest): POST con body JSON `{usuario_id: int, comentario?: str}`.
        asignacion_id (int): PK de la AsignacionAnalista a reemplazar.

    Returns:
        JsonResponse: `{success: true, message: str}` en éxito.
            Errores posibles: 405, 400 (JSON), 403 (no líder), 404 (asignación/usuario),
            400 (usuario fuera del grupo), 500 (error interno).

    Lógica crítica:
        - Usa `transaction.atomic()` correctamente: la cancelación y la nueva creación
          son atómicas.
        - El filtro `estado__in=['analista_asignado', 'proceso_analisis', 'proceso_empate']` en la obtención de la
          asignación garantiza que no se puedan reemplazar asignaciones ya finalizadas
          o canceladas.
        - El estado de la solicitud no se actualiza explícitamente (se mantiene el estado
          actual), solo cambian los campos `usuario_analista` y `usuario_asignado`.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    asignacion = get_object_or_404(
        AsignacionAnalista.objects.select_related('solicitud'),
        id=asignacion_id,
        estado__in=['analista_asignado', 'proceso_analisis', 'proceso_empate'],
    )
    solicitud = asignacion.solicitud

    if not request.user.is_superuser:
        grupo_analisis = Grupo.objects.filter(
            lider=request.user,
            nombre__icontains='ANALISIS',
            activo=True
        ).first()
        if not grupo_analisis:
            return JsonResponse({'error': 'No es líder de ningún grupo ANALISIS activo'}, status=403)
    else:
        grupo_analisis = Grupo.objects.filter(
            nombre__icontains='ANALISIS', activo=True
        ).first()

    try:
        data = json.loads(request.body)
        usuario_id = data.get('usuario_id')
        comentario = data.get('comentario', '')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)

    nuevo_usuario = get_object_or_404(User, id=usuario_id, estado='ACTIVO', is_active=True)

    if grupo_analisis and nuevo_usuario not in grupo_analisis.usuarios.all():
        return JsonResponse({'error': 'El usuario no pertenece al grupo ANALISIS'}, status=400)

    if nuevo_usuario == request.user:
        return JsonResponse({'error': 'No puede asignarse a sí mismo'}, status=400)

    try:
        with transaction.atomic():
            # Cancelar asignación actual
            asignacion.estado = 'analisis_cancelado'
            asignacion.fecha_termino = timezone.now()
            asignacion.save(update_fields=['estado', 'fecha_termino'])

            # Crear nueva asignación
            orden_ot = solicitud.ordenes_trabajo.filter(
                estado='completada', activa=False
            ).order_by('-fecha_creacion').first()
            AsignacionAnalista.objects.create(
                solicitud=solicitud,
                orden_trabajo=orden_ot,
                analista=nuevo_usuario,
                lider_asignador=request.user,
                estado='analista_asignado',
                observaciones=comentario,
            )

            # Actualizar solicitud
            solicitud._auditoria_creada = True
            solicitud._cambiado_por = request.user
            solicitud.usuario_analista = nuevo_usuario
            solicitud.usuario_asignado = nuevo_usuario
            solicitud.ultima_asignacion_por = request.user
            solicitud.fecha_asignacion = timezone.now()
            solicitud.save()

            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='cambio_analista',
                valor_anterior=asignacion.analista.username if asignacion.analista else 'Ninguno',
                valor_nuevo=f"{nuevo_usuario.username} (cambiado por: {request.user.username})",
                cambiado_por=request.user,
                comentario=comentario or f"Cambio de analista realizado por {request.user.username}"
            )
    except Exception as e:
        return JsonResponse({'error': f'Error al cambiar analista: {str(e)}'}, status=500)

    return JsonResponse({
        'success': True,
        'message': f'Analista cambiado a {nuevo_usuario.get_full_name() or nuevo_usuario.username}'
    })


@login_required
@requiere_ser_lider_analisis
def eliminar_asignacion_analista(request, solicitud_id):
    """Eliminar asignación de usuario (solo para líderes del grupo)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)
    comentario = request.POST.get('comentario', '')

    estados_activos = ['analista_asignado', 'proceso_analisis', 'proceso_empate']
    asignacion_activa = AsignacionAnalista.objects.filter(
        solicitud=solicitud,
        estado__in=estados_activos,
    ).order_by('-fecha_asignacion').first()

    if not asignacion_activa:
        return JsonResponse({
            'error': 'No existe una asignacion activa para eliminar.'
        }, status=400)

    # Verificar que el usuario sea líder del grupo asignado (o superusuario)
    if not (solicitud.grupo_asignado and (solicitud.grupo_asignado.lider == request.user or request.user.is_superuser)):
        return JsonResponse({
            'error': 'No es líder del grupo asignado'
        }, status=403)

    # Guardar información para auditoría
    usuario_anterior = asignacion_activa.analista
    asignado_por_anterior = asignacion_activa.lider_asignador

    # Cancelar asignación activa y devolver solicitud a pendiente.
    with transaction.atomic():
        asignacion_activa.estado = 'analisis_cancelado'
        asignacion_activa.fecha_termino = timezone.now()
        asignacion_activa.save(update_fields=['estado', 'fecha_termino'])

        solicitud.usuario_analista = None
        solicitud.usuario_asignado = None
        solicitud.ultima_asignacion_por = None
        solicitud.fecha_asignacion = None
        solicitud.estado = 'pendiente_asignacion_analista'
        solicitud.save(update_fields=[
            'usuario_analista',
            'usuario_asignado',
            'ultima_asignacion_por',
            'fecha_asignacion',
            'estado',
        ])

    # Crear auditoría
    SolicitudRelevamientoAudit.objects.create(
        solicitud=solicitud,
        campo='usuario_analista',
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
@requiere_ser_lider_analisis
@require_POST
def validar_analisis_colonia(request, solicitud_id):
    """Valida y finaliza una asignacion de Analisis, pasando la solicitud a aprobada para campo."""
    try:
        data = json.loads(request.body)
        observacion = data.get('observacion', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Datos JSON invalidos'}, status=400)

    solicitud = get_object_or_404(
        SolicitudRelevamiento.objects.select_related('grupo_asignado'),
        id=solicitud_id,
    )

    if not (solicitud.grupo_asignado and (solicitud.grupo_asignado.lider == request.user or request.user.is_superuser)):
        return JsonResponse({'success': False, 'message': 'No tiene permisos para validar esta solicitud.'}, status=403)

    estados_activos = ['analista_asignado', 'proceso_analisis', 'proceso_empate']
    asignacion_activa = AsignacionAnalista.objects.filter(
        solicitud=solicitud,
        estado__in=estados_activos,
    ).order_by('-fecha_asignacion').first()

    if not asignacion_activa:
        return JsonResponse({'success': False, 'message': 'No existe asignacion activa para validar.'}, status=400)

    try:
        with transaction.atomic():
            estado_anterior = solicitud.estado

            asignacion_activa.estado = 'analisis_finalizado'
            asignacion_activa.fecha_termino = timezone.now()
            if observacion:
                nota = f"VALIDADO por {request.user.username}: {observacion}"
                asignacion_activa.observaciones = f"{(asignacion_activa.observaciones or '').strip()}\n\n{nota}".strip()
            asignacion_activa.save(update_fields=['estado', 'fecha_termino', 'observaciones'])

            solicitud.estado = 'aprobado_para_campo'
            solicitud.fecha_aprobacion_campo = timezone.now()

            if observacion:
                marca_tiempo = timezone.now().strftime('%d/%m/%Y %H:%M')
                nota_solicitud = f"VALIDACION ANALISIS ({marca_tiempo}) por {request.user.username}:\n{observacion}"
                solicitud.observaciones = f"{(solicitud.observaciones or '').strip()}\n\n--- {nota_solicitud}".strip()

            solicitud.save(update_fields=['estado', 'fecha_aprobacion_campo', 'observaciones'])

            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='estado',
                valor_anterior=estado_anterior,
                valor_nuevo=solicitud.estado,
                cambiado_por=request.user,
                comentario=f"Analisis validado por {request.user.username}. {observacion if observacion else 'Sin observaciones'}",
            )

        return JsonResponse({
            'success': True,
            'message': 'Analisis validado correctamente. Solicitud aprobada para campo.',
            'nuevo_estado': solicitud.estado,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al validar analisis: {str(e)}'}, status=500)


@login_required
@requiere_ser_lider_analisis
@require_POST
def generar_dictamen_analisis(request, solicitud_id):
    """Registra un dictamen tecnico en la asignacion activa de Analisis."""
    try:
        data = json.loads(request.body)
        dictamen = data.get('dictamen', '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Datos JSON invalidos'}, status=400)

    if not dictamen:
        return JsonResponse({'success': False, 'message': 'El dictamen tecnico es obligatorio.'}, status=400)

    solicitud = get_object_or_404(SolicitudRelevamiento.objects.select_related('grupo_asignado'), id=solicitud_id)

    if not (solicitud.grupo_asignado and (solicitud.grupo_asignado.lider == request.user or request.user.is_superuser)):
        return JsonResponse({'success': False, 'message': 'No tiene permisos para generar dictamen.'}, status=403)

    estados_validos = ['analista_asignado', 'proceso_analisis', 'proceso_empate', 'analisis_finalizado']
    asignacion = AsignacionAnalista.objects.filter(
        solicitud=solicitud,
        estado__in=estados_validos,
    ).order_by('-fecha_asignacion').first()

    if not asignacion:
        return JsonResponse({'success': False, 'message': 'No existe asignacion para registrar dictamen.'}, status=400)

    try:
        with transaction.atomic():
            marca_tiempo = timezone.now().strftime('%d/%m/%Y %H:%M')
            texto_dictamen = f"DICTAMEN TECNICO ({marca_tiempo}) por {request.user.username}:\n{dictamen}"

            asignacion.observaciones = f"{(asignacion.observaciones or '').strip()}\n\n{texto_dictamen}".strip()
            asignacion.save(update_fields=['observaciones'])

            solicitud.observaciones = f"{(solicitud.observaciones or '').strip()}\n\n--- {texto_dictamen}".strip()
            solicitud.save(update_fields=['observaciones'])

            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='dictamen_analisis',
                valor_anterior='-',
                valor_nuevo='Dictamen tecnico registrado',
                cambiado_por=request.user,
                comentario=dictamen,
            )

        return JsonResponse({
            'success': True,
            'message': 'Dictamen tecnico registrado correctamente.',
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al registrar dictamen: {str(e)}'}, status=500)


# Vista de solicitudes para usuarios Analisis NO CORRESPONDE TODAVIA

@login_required
@requiere_ser_analisis
def analisis_solicitudes(request):
    """
    Vista de gestión completa de solicitudes para el módulo de Análisis.
    Accesible para todos los miembros del grupo (analistas y líderes).

    Propósito y flujo de datos:
        1. Construye `query` base: solicitudes con `grupo_asignado` en los grupos ANALISIS
           del usuario, con `select_related` y `prefetch_related` para evitar N+1 en datos
           geográficos.
        2. Construye querysets separados por estado (pendientes, asignadas, en_proceso,
           pendiente_revision, aprobadas, rechazadas, finalizadas).
        3. Itera cada queryset para inyectar propiedades calculadas en cada solicitud:
           `puede_asignar_lider`, `puede_cambiar_asignacion`, `puede_eliminar_asignacion`,
           `acciones_revision`, `inicio_analisis`, `fin_analisis`, `tiempo_analisis_mostrar`.
        4. Si no es líder, filtra `asignadas` y `en_proceso` al usuario actual.
        5. Calcula `urgentes` iterando nuevamente cada queryset (segunda evaluación).

    Variables de contexto (template context):
        es_lider (bool): True si el usuario es líder del grupo.
        grupos_usuario (QuerySet[Grupo]): Grupos ANALISIS activos del usuario.
        estadisticas (dict): Conteos por estado (total, pendientes, en_proceso,
            pendiente_revision, aprobadas, rechazadas, finalizadas).
        usuarios_grupo (QuerySet[User]): Usuarios activos del grupo excluyendo al usuario
            actual. Solo para líderes.
        solicitudes_pendientes (QuerySet): Estado 'pendiente_asignacion_analista'.
        solicitudes_asignadas (QuerySet): Estado 'asignado_a_analista'.
        solicitudes_en_proceso (QuerySet): Estado 'en_proceso_analisis'.
        solicitudes_revision (QuerySet): Estado 'pendiente_revision_analisis'.
        solicitudes_aprobadas (QuerySet): Con `fecha_aprobacion_campo` no nula.
        solicitudes_rechazadas (QuerySet): Estado 'rechazado' del grupo o sus analistas.
        solicitudes_finalizadas (QuerySet): Con `fecha_aprobacion_campo` no nula (base query).
        urgentes (dict): Conteo de solicitudes urgentes por estado (días superados).

    Lógica crítica:
        - Las propiedades inyectadas dinámicamente en las instancias del modelo
          (ej. `solicitud.puede_asignar_lider`) son atributos ad-hoc que no existen
          en el modelo; dependen de que los querysets se evalúen en Python antes del
          render. Son frágiles ante cambios en el modelo.
        - El cálculo de `tiempo_analisis_mostrar` usa un bloque try/except genérico
          que silencia cualquier error, dificultando el debugging.
        - `query_aprobadas` filtra por `fecha_aprobacion_campo__isnull=False` con
          un OR que incluye un JOIN M2M, luego aplica `distinct()`, lo que puede
          generar un plan de ejecución ineficiente en PostgreSQL.

    Cuellos de botella (query efficiency):
        - CRÍTICO: Double queryset evaluation. El loop de propiedades evalúa cada
          queryset una vez; luego `urgentes = {key: sum(1 for s in qs if s.es_urgente()) ...}`
          los evalúa una segunda vez. Con 7 estados, esto genera hasta 14 hits a la BD
          en lugar de 7. Solución: convertir los querysets a listas antes del primer loop
          (`estados = {k: list(v) for k, v in estados.items()}`).
        - ALTO: `rechazadas_qs` y `query_aprobadas` usan `distinct()` con OR sobre
          relaciones M2M/FK múltiples. En tablas con miles de registros, el DISTINCT
          puede degradar el rendimiento. Considerar subconsultas o `union()`.
        - MEDIO: `estadisticas = {key: qs.count() for key, qs in estados.items()}` lanza
          un COUNT(*) por estado (7 queries adicionales). Si los estados ya fueron
          evaluados a listas, usar `len()` en lugar de `.count()`.
        - BAJO: `es_urgente()` es pura Python (usa `fecha_creacion`, campo ya cargado),
          pero se llama N veces en el loop de `urgentes`. No genera queries adicionales.
    """
    grupos_usuario = Grupo.objects.filter(
        (Q(usuarios__id=request.user.id) | Q(lider=request.user)),
        nombre__icontains='ANALISIS',
        activo=True
    ).distinct()

    if not grupos_usuario.exists():
        messages.warning(request, "No pertenece a ningún grupo Análisis activo.")
        return render(request, 'includes/analisis/tablas/solicitudes_relevamiento_analisis.html', {
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
            Q(asignaciones_analista__analista__in=miembros)
        ).distinct()
    except Exception:
        rechazadas_qs = rechazadas_qs.filter(grupo_asignado__in=grupos_usuario)

    estados = {
        'pendientes': query.filter(estado='pendiente_asignacion_analista'),
        'asignadas': query.filter(estado='asignado_a_analista'),
        'en_proceso': query.filter(estado='en_proceso_analisis'),
        'pendiente_revision': query.filter(estado='pendiente_revision_analisis'),
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
                solicitud.estado in ['pendiente_asignacion_analisis', 'rechazado']
            )

            # Determinar si se puede cambiar asignación
            solicitud.puede_cambiar_asignacion = (
                es_lider and
                solicitud.estado == 'asignado_a_analista'
            )

            # Determinar si se puede eliminar asignación
            solicitud.puede_eliminar_asignacion = (
                es_lider and
                solicitud.estado == 'asignado_a_analista'
            )

            # Determinar acciones de revisión disponibles
            if es_lider:
                if solicitud.estado == 'en_proceso_analisis':
                    solicitud.acciones_revision = [
                        'aprobar_revision', 'devolver_correccion', 'rechazar_revision']
                elif solicitud.estado == 'pendiente_revision_analisis':
                    solicitud.acciones_revision = [
                        'aprobar_revision', 'rechazar_revision']
                else:
                    solicitud.acciones_revision = []

            # Calcular tiempos para la tabla de revisión (inicio/fin/elapsed)
            try:
                inicio = solicitud.fecha_inicio_etapa
                # si hay inicio y duración registrada, calcular fin
                if inicio and solicitud.tiempo_analisis:
                    fin = inicio + solicitud.tiempo_analisis
                else:
                    fin = None

                # elegir tiempo a mostrar: tiempo_digitalizacion si existe, sino tiempo en la etapa actual
                if solicitud.tiempo_analisis:
                    tiempo_mostrar = solicitud.tiempo_analisis
                else:
                    # llamar al método que devuelve tiempo en la etapa actual
                    try:
                        tiempo_mostrar = solicitud.obtener_tiempo_etapa_actual()
                    except Exception:
                        tiempo_mostrar = None

                solicitud.inicio_analisis = inicio
                solicitud.fin_analisis = fin
                solicitud.tiempo_analisis_mostrar = tiempo_mostrar
            except Exception:
                solicitud.inicio_analisis = None
                solicitud.fin_analisis = None
                solicitud.tiempo_analisis_mostrar = None

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
        ).exclude(id=request.user.id).order_by('username')

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

    return render(request, 'includes/analisis/tablas/solicitudes_relevamiento_analisis.html', context)


@login_required
@requiere_ser_analisis
def colonias_relevadas_analisis(request):
    """
    Vista de gestión de colonias relevadas para el módulo de Análisis.
    Presenta tres secciones: Pendientes (sin asignación), Asignadas (activas), Terminadas.

    Propósito y flujo de datos:
        1. Obtiene OT completadas (misma fuente canónica que `analisis_dashboard`).
        2. Pre-calcula dos conjuntos Python (`sol_ids_asignadas`, `sol_ids_terminadas`)
           con los IDs de solicitudes que ya tienen asignaciones de análisis activas
           o finalizadas, para clasificar las colonias en la siguiente iteración.
        3. Itera las OT completadas; las colonias sin asignación van a `colonias_pendientes`
           (lista de dicts). Aplica deduplicación por `colonia.id` con `seen_colonias`.
        4. Consulta `AsignacionAnalisis` para las listas de asignadas y terminadas,
           con `select_related` y `prefetch_related` para los datos geográficos.
        5. Si no es líder: filtra asignaciones al usuario actual y vacía `colonias_pendientes`.

    Variables de contexto (template context):
        es_lider (bool): True si es líder de algún grupo ANALISIS activo.
        grupos_usuario (QuerySet[Grupo]): Grupos ANALISIS activos del usuario.
        estadisticas (dict): `{pendientes: int, asignadas: int, terminadas: int}`.
        usuarios_grupo (QuerySet[User]): Usuarios activos del grupo (sin el usuario actual).
            Solo para líderes.
        colonias_pendientes (list[dict]): Colonias con OT completada pero sin asignación
            de análisis. Cada dict: solicitud_id, colonia_nombre, distrito_nombre,
            departamento_nombre, fecha_relevada, coordinador_campo, puede_asignar_lider.
            Vacío para analistas no líderes.
        asignaciones_activas (QuerySet[AsignacionAnalisis]): Asignaciones en estado
            'asignado' o 'en_proceso'. Filtrado al usuario si no es líder.
        asignaciones_terminadas (QuerySet[AsignacionAnalisis]): Asignaciones en estado
            'finalizado'. Filtrado al usuario si no es líder.

    Lógica crítica:
        - La clasificación de colonias en "pendientes" depende de que `sol_ids_asignadas`
          y `sol_ids_terminadas` sean conjuntos completos. Si una solicitud tiene
          asignaciones tanto activas como terminadas, aparece solo en terminadas (correcto).
        - `puede_asignar_lider` en cada dict de `colonias_pendientes` siempre es igual
          a `es_lider`, por lo que es redundante en el contexto actual. Podría eliminarse
          del dict y usarse directamente la variable `es_lider` en el template.

    Cuellos de botella (query efficiency):
        - MEDIO: `sol_ids_asignadas` y `sol_ids_terminadas` se cargan como conjuntos
          Python completos (`set(values_list(...))`). Con miles de asignaciones, el
          tamaño en memoria crece linealmente. Considerar filtrar directamente en la
          query de OT usando `exclude(solicitud__asignaciones_analista__estado__in=[...])`.
        - BAJO: La misma observación de `colonia.distritos.first()` del dashboard aplica
          aquí: verificar que el prefetch cubra este acceso.
        - BAJO: `estadisticas['pendientes'] = len(colonias_pendientes)` es O(n) en Python
          pero ya está construida la lista, por lo que es correcto y eficiente.
    """
    grupos_usuario = Grupo.objects.filter(
        (Q(usuarios__id=request.user.id) | Q(lider=request.user)),
        nombre__icontains='ANALISIS',
        activo=True
    ).distinct()

    if not grupos_usuario.exists():
        messages.warning(request, "No pertenece a ningún grupo ANALISIS activo.")
        return render(request, 'includes/analisis/tablas/colonias_relevadas_analisis.html', {
            'estadisticas': {},
            'es_lider': False
        })

    es_lider = grupos_usuario.filter(lider=request.user).exists()

    # -------------------------------------------------------
    # Fuente canónica: OT completadas de tipo=relevamiento
    # (idéntica lógica al analisis_dashboard)
    # -------------------------------------------------------
    ordenes_completadas = OrdenTrabajo.objects.filter(
        estado='completada',
        activa=False,
        solicitud__tipo='relevamiento',
    ).select_related(
        'solicitud__colonia',
        'coordinador_responsable',
    ).prefetch_related(
        'solicitud__colonia__distritos__departamento',
        'equipos_asignados__coordinador_campo',
    ).order_by('solicitud__colonia__nombre', '-fecha_creacion')

    # Colonias con asignación activa de analista.
    # Solo estas se excluyen de "Pendientes" para mostrar únicamente
    # colonias que hoy no cuentan con analista asignado.
    colonias_con_analista_asignado = set(
        AsignacionAnalista.objects.filter(
            analista__isnull=False,
            estado__in=['analista_asignado', 'proceso_analisis', 'proceso_empate']
        ).values_list('solicitud__colonia_id', flat=True)
    )

    # Construir lista de colonias (una por colonia, usando la OT más reciente)
    seen_colonias = set()
    colonias_pendientes = []

    for orden in ordenes_completadas:
        sol = orden.solicitud
        if not sol or not sol.colonia:
            continue
        colonia = sol.colonia
        if colonia.id in seen_colonias:
            continue
        seen_colonias.add(colonia.id)

        # Sólo va a "Pendientes" si la colonia no tiene analista activo asignado.
        if colonia.id in colonias_con_analista_asignado:
            continue

        distrito = colonia.distritos.first()
        departamento = distrito.departamento if distrito else None

        equipo = orden.equipos_asignados.first()
        if equipo and getattr(equipo, 'coordinador_campo', None):
            u = equipo.coordinador_campo
            coord_nombre = f"{u.first_name} {u.last_name}".strip() or u.username
        elif orden.coordinador_responsable:
            u = orden.coordinador_responsable
            coord_nombre = f"{u.first_name} {u.last_name}".strip() or u.username
        else:
            coord_nombre = 'Sin coordinador'

        colonias_pendientes.append({
            'solicitud_id': sol.id,
            'colonia_nombre': colonia.nombre,
            'distrito_nombre': distrito.nombre if distrito else 'Sin distrito',
            'departamento_nombre': departamento.nombre if departamento else 'Sin departamento',
            'fecha_relevada': orden.fecha_fin_real,
            'coordinador_campo': coord_nombre,
            'puede_asignar_lider': es_lider,
        })

    # Asignadas y Terminadas desde AsignacionAnalisis
    asignaciones_activas = AsignacionAnalista.objects.filter(
        solicitud__tipo='relevamiento',
        solicitud__ordenes_trabajo__estado='completada',
        estado__in=['analista_asignado', 'proceso_analisis', 'proceso_empate']
    ).distinct().select_related(
        'solicitud__colonia', 'analista', 'lider_asignador'
    ).prefetch_related('solicitud__colonia__distritos__departamento')

    asignaciones_terminadas = AsignacionAnalista.objects.filter(
        solicitud__tipo='relevamiento',
        solicitud__ordenes_trabajo__estado='completada',
        estado='analisis_finalizado'
    ).distinct().select_related(
        'solicitud__colonia', 'analista', 'lider_asignador'
    ).prefetch_related('solicitud__colonia__distritos__departamento')

    if not es_lider:
        asignaciones_activas = asignaciones_activas.filter(analista=request.user)
        asignaciones_terminadas = asignaciones_terminadas.filter(analista=request.user)
        colonias_pendientes = []  # analistas sólo ven sus asignaciones

    estadisticas = {
        'pendientes': len(colonias_pendientes),
        'asignadas': asignaciones_activas.count(),
        'terminadas': asignaciones_terminadas.count(),
    }

    usuarios_grupo = []
    if es_lider and grupos_usuario.exists():
        grupo_principal = grupos_usuario.first()
        usuarios_grupo = grupo_principal.usuarios.filter(
            estado='ACTIVO',
            is_active=True
        ).exclude(id=request.user.id).order_by('username')

    context = {
        'es_lider': es_lider,
        'grupos_usuario': grupos_usuario,
        'estadisticas': estadisticas,
        'usuarios_grupo': usuarios_grupo,
        'colonias_pendientes': colonias_pendientes,
        'asignaciones_activas': asignaciones_activas,
        'asignaciones_terminadas': asignaciones_terminadas,
    }

    return render(request, 'includes/analisis/tablas/colonias_relevadas_analisis.html', context)

