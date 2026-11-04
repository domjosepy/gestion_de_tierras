from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils import timezone as tz
from coordinacion.models import OrdenTrabajo
from .decorators import encuestador_required, coordinador_campo_required
from django.forms import inlineformset_factory
from .models import (
    Relevamiento, Documento,
    Pretendiente, Vivienda, Miembro, Cultivo, ProduccionGanadera,
    InstitucionEnLote, ArchivoSubcoordinador,
    USO_LOTE_OCUPANTE_CHOICES, MEJORAS_CHOICES, EQUIPAMIENTOS_CHOICES,
    RELACION_CON_LOTE_CHOICES, USO_LOTE_SERVICIO_CHOICES
)
from .forms import (RelevamientoParte1Form, RelevamientoParte2Form,
    RelevamientoMejorasForm,RelevamientoConflictoParte1Form, PretendienteIdentificacionForm,
    PretendienteMejorasForm, RelevamientoCierreForm, 
    RelevamientoServicioParte1Form, ViviendaForm, MiembroForm, CultivoForm, 
    ProduccionGanaderaForm, InstitucionEnLoteForm, FotosRelevamientoForm,
)
from django.db import transaction, IntegrityError
from gerencia.models import SolicitudRelevamientoAudit, SolicitudRelevamiento
from administrador.models import Grupo
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse
import os, re, json, logging
logger = logging.getLogger(__name__)
# ─────────────────────────────────────────────
# DASHBOARD COORDINADOR DE CAMPO
# ─────────────────────────────────────────────

@login_required
@coordinador_campo_required
def coordinador_campo_dashboard(request):
    """
    Dashboard para coordinadores de campo: muestra todas las órdenes donde
    el usuario está asignado como coordinador de campo.
    """
    
    # Filtrar órdenes donde el usuario es coordinador_campo en la solicitud
    ordenes = (
        OrdenTrabajo.objects
        .exclude(estado__in=['cancelada'])
        .filter(solicitud__coordinador_campo=request.user)
        .select_related(
            'solicitud',
            'solicitud__colonia',
            'solicitud__coordinador_campo',
        )
        .prefetch_related(
            'equipos_asignados',
            'equipos_asignados__subcoordinadores',
            'equipos_asignados__encuestadores',
        )
        .order_by('-fecha_creacion')
    )

    # Preparar contexto enriquecido para cada orden
    ordenes_context = []
    for orden in ordenes:
        # Obtener datos geográficos
        datos_geo = datos_geograficos_desde_orden(orden)
        
        # Contar personal asignado
        equipos = orden.equipos_asignados.all()
        subcoordinadores_count = 0
        encuestadores_count = 0
        subcoordinadores_list = []
        encuestadores_list = []
        for equipo in equipos:
            subcoordinadores_count += equipo.subcoordinadores.count()
            encuestadores_count += equipo.encuestadores.count()
            # recopilar nombres (manteniendo orden y evitando duplicados más abajo)
            subcoordinadores_list.extend(list(equipo.subcoordinadores.all()))
            encuestadores_list.extend(list(equipo.encuestadores.all()))
        
        # Contar relevamientos de esta orden
        relevamientos_count = Relevamiento.objects.filter(orden_trabajo=orden).count()
        
        ordenes_context.append({
            'orden': orden,
            'datos_geo': datos_geo,
            'subcoordinadores_count': subcoordinadores_count,
            'encuestadores_count': encuestadores_count,
            'subcoordinadores_list': list(dict.fromkeys(subcoordinadores_list)),
            'encuestadores_list': list(dict.fromkeys(encuestadores_list)),
            'relevamientos_count': relevamientos_count,
        })

    context = {
        'ordenes_context': ordenes_context,
        'total_ordenes': ordenes.count(),
    }
    return render(request, 'relevamiento/coordinador_dashboard.html', context)

@login_required
@coordinador_campo_required
def habilitar_formulario_relevamiento(request, orden_id):
    """
    Habilita o deshabilita el formulario de relevamiento para una orden.
    Solo el coordinador de campo asignado puede hacerlo.
    """
    orden = get_object_or_404(OrdenTrabajo, pk=orden_id)
    
    # Verificar que el usuario es el coordinador de campo de esta orden
    if orden.solicitud.coordinador_campo != request.user and not request.user.is_superuser:
        messages.error(request, 'No tiene permisos para modificar esta orden.')
        return redirect('relevamiento:coordinador_dashboard')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Toggle del estado
                orden.formulario_habilitado = not orden.formulario_habilitado
                orden.save()

                solicitud = orden.solicitud

                if orden.formulario_habilitado:
                    # Habilitado -> pasar solicitud a ejecución en campo y orden a en_proceso
                    previo = solicitud.estado if solicitud else None
                    if solicitud:
                        solicitud.estado = 'en_ejecucion_campo'
                        solicitud.save()
                    

                    orden.estado = 'en_proceso'
                    orden.fecha_inicio_real = timezone.now().date()
                    orden.save()

                    # Auditoría
                    try:
                        SolicitudRelevamientoAudit.objects.create(
                            solicitud=solicitud,
                            campo='formulario_habilitado',
                            valor_anterior=previo or '',
                            valor_nuevo='en_ejecucion_campo',
                            cambiado_por=request.user,
                            comentario=f'Formulario habilitado por {request.user.username}'
                        )
                    except Exception:
                        pass

                    messages.success(request, 'Formulario habilitado. Solicitud en ejecución de campo y orden en proceso.')
                else:
                    # Deshabilitado -> pasar solicitud a pendiente_cierre
                    previo = solicitud.estado if solicitud else None
                    if solicitud:
                        solicitud.estado = 'pendiente_cierre'
                        solicitud.save()


                    # Auditoría
                    try:
                        SolicitudRelevamientoAudit.objects.create(
                            solicitud=solicitud,
                            campo='formulario_habilitado',
                            valor_anterior=previo or '',
                            valor_nuevo='pendiente_cierre',
                            cambiado_por=request.user,
                            comentario=f'Formulario deshabilitado por {request.user.username}'
                        )
                    except Exception:
                        pass

                    messages.success(request, 'Formulario deshabilitado. Solicitud marcada como pendiente de cierre.')

            return redirect('relevamiento:coordinador_dashboard')
        except Exception as e:
            messages.error(request, f'Error al cambiar estado del formulario: {str(e)}')
            return redirect('relevamiento:coordinador_dashboard')
    
    return redirect('relevamiento:coordinador_dashboard')

@login_required
@coordinador_campo_required
def finalizar_orden_campo(request, orden_id):
    """
    Finaliza una orden de trabajo y reasigna la solicitud al grupo de análisis.
    Solo el coordinador de campo puede hacerlo.
    """

    orden = get_object_or_404(OrdenTrabajo, pk=orden_id)
    solicitud = orden.solicitud
    
    # Verificar que el usuario es el coordinador de campo
    if solicitud.coordinador_campo != request.user and not request.user.is_superuser:
        messages.error(request, 'No tiene permisos para finalizar esta orden.')
        return redirect('relevamiento:coordinador_dashboard')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Cambiar estado de la orden a completada
                orden.estado = 'completada'
                orden.fecha_fin_real = timezone.now().date()
                orden.formulario_habilitado = False  # Deshabilitar formulario al finalizar
                orden.activa = False
                orden.save()
                
                # Asignar solicitud al grupo de análisis
                try:
                    grupo_analisis = Grupo.objects.filter(
                        nombre__icontains='ANALISIS',
                        activo=True
                    ).first()

                    if grupo_analisis:
                        solicitud.estado = 'finalizado'

                        # Marcar la solicitud según su tipo como terminada
                        if solicitud.tipo == SolicitudRelevamiento.TIPO_RELEVAMIENTO:
                            solicitud.relevamiento_terminado = True
                            # luego mantener al coordinador de campo como el usuario asignado 
                            # para que pueda hacer seguimiento desde la solicitud
                            solicitud.usuario_asignado = solicitud.coordinador_campo
                            
                        elif solicitud.tipo == SolicitudRelevamiento.TIPO_ACTUALIZACION:
                            solicitud.actualizacion_terminado = True
                            solicitud.usuario_asignado = None  # No asignar a nadie para actualizaciones, asignaremos a análisis: lider
                        solicitud.save()
                        # Si existen otras solicitudes para la misma colonia creadas
                        # posteriormente a esta solicitud, marcarlas como actualización
                        try:
                            otras = SolicitudRelevamiento.objects.filter(
                                colonia=solicitud.colonia
                            ).exclude(pk=solicitud.pk).filter(fecha_creacion__gte=solicitud.fecha_creacion)

                            for otra in otras:
                                tipo_anterior = otra.tipo
                                if tipo_anterior != SolicitudRelevamiento.TIPO_ACTUALIZACION:
                                    otra.tipo = SolicitudRelevamiento.TIPO_ACTUALIZACION
                                    otra.save()
                                    # Registrar auditoría por el cambio de tipo
                                    try:
                                        SolicitudRelevamientoAudit.objects.create(
                                            solicitud=otra,
                                            campo='tipo',
                                            valor_anterior=tipo_anterior,
                                            valor_nuevo=SolicitudRelevamiento.TIPO_ACTUALIZACION,
                                            cambiado_por=request.user,
                                            comentario=f"Tipo marcado como 'actualizacion' al finalizar orden {orden.numero_orden}"
                                        )
                                    except Exception:
                                        # No interrumpimos el flujo por fallo en auditoría
                                        pass
                        except Exception as e:
                            messages.warning(request, f'No se pudo actualizar tipo de otras solicitudes: {str(e)}')
                        
                        # Registrar auditoría
                        SolicitudRelevamientoAudit.objects.create(
                            solicitud=solicitud,
                            campo='finalizacion_campo',
                            valor_anterior='en_ejecucion_campo',
                            valor_nuevo='finalizado',
                            cambiado_por=request.user,
                            comentario=f'Orden finalizada por coordinador de campo: {request.user.username}'
                        )
                        
                        messages.info(
                            request,
                            f'Orden {orden.numero_orden} finalizada.'
                        )
                        
                    else:
                        messages.warning(
                            request,
                            'Orden finalizada, pero no se encontró el grupo de Análisis para reasignación.'
                        )
                except Exception as e:
                    messages.error(request, f'Error al reasignar a análisis: {str(e)}')
                    
        except Exception as e:
            messages.error(request, f'Error al finalizar la orden: {str(e)}')
    
    return redirect('relevamiento:coordinador_dashboard')

@login_required
@coordinador_campo_required
def detalle_relevamiento_coordinador(request, orden_id):
    """
    Vista detallada de relevamiento para coordinador de campo.
    Muestra resumen por encuestador y subcoordinador.
    """
    orden = get_object_or_404(
        OrdenTrabajo.objects.select_related(
            'solicitud__colonia',
            'coordinador_responsable'
        ).prefetch_related(
            'equipos_asignados__subcoordinadores',
            'equipos_asignados__encuestadores'
        ),
        id=orden_id
    )
    
    # Datos geográficos
    datos_geo = datos_geograficos_desde_orden(orden)
    
    # Personal asignado
    subcoordinadores = []
    encuestadores = []
    for equipo in orden.equipos_asignados.all():
        subcoordinadores.extend(equipo.subcoordinadores.all())
        encuestadores.extend(equipo.encuestadores.all())
    
    # Eliminar duplicados manteniendo orden
    subcoordinadores = list(dict.fromkeys(subcoordinadores))
    encuestadores = list(dict.fromkeys(encuestadores))
    
    # Base de relevamientos de la orden para conteos consistentes
    relevamientos_orden = Relevamiento.objects.filter(orden_trabajo=orden)

    # Resumen por encuestador
    encuestadores_stats = []
    for encuestador in encuestadores:
        # Contar encuestas de esta orden por este encuestador
        total_encuestas = relevamientos_orden.filter(
            encuestador=encuestador,
        ).count()

        # Contar solicitudes firmadas por este encuestador en la orden
        total_solicitudes = relevamientos_orden.filter(
            encuestador=encuestador,
            firmo_solicitud=True,
        ).count()
        
        # Contar fotos registradas por este encuestador en esta orden
        total_fotos = Documento.objects.filter(
            relevamiento__encuestador=encuestador,
            relevamiento__orden_trabajo=orden,
            tipo__in=['recibo', 'vivienda', 'documento', 'lote']
        ).count()
        
        encuestadores_stats.append({
            'encuestador': encuestador,
            'total_encuestas': total_encuestas,
            'total_solicitudes': total_solicitudes,
            'total_fotos': total_fotos,
        })
    
    # Resumen por subcoordinador
    subcoordinadores_stats = []
    for subcoordinador in subcoordinadores:
        # Contar archivos subidos por este subcoordinador en esta orden
        total_archivos = ArchivoSubcoordinador.objects.filter(
            subido_por=subcoordinador,
            orden_trabajo=orden
        ).count()
        
        subcoordinadores_stats.append({
            'subcoordinador': subcoordinador,
            'total_archivos': total_archivos,
        })
    
    # Totales ejecutivos para la cabecera y exportaciones
    total_encuestas_orden = relevamientos_orden.count()
    total_solicitudes = relevamientos_orden.filter(firmo_solicitud=True).count()
    total_fotos_orden = Documento.objects.filter(
        relevamiento__orden_trabajo=orden,
        tipo__in=['recibo', 'vivienda', 'documento', 'lote']
    ).count()
    total_archivos_subcoordinadores = ArchivoSubcoordinador.objects.filter(
        orden_trabajo=orden
    ).count()

    context = {
        'orden': orden,
        'datos_geo': datos_geo,
        'subcoordinadores': subcoordinadores,
        'encuestadores': encuestadores,
        'encuestadores_stats': encuestadores_stats,
        'subcoordinadores_stats': subcoordinadores_stats,
        'total_encuestas_orden': total_encuestas_orden,
        'total_solicitudes': total_solicitudes,
        'total_fotos_orden': total_fotos_orden,
        'total_archivos_subcoordinadores': total_archivos_subcoordinadores,
    }
    
    return render(request, 'includes/relevamiento/coordinador/detalle_relevamiento.html', context)

# ─────────────────────────────────────────────
# DASHBOARD SUBCOORDINADOR
# ─────────────────────────────────────────────
@login_required
def subcoordinador_dashboard(request):
    """
    Dashboard para subcoordinadores: muestra las colonias asignadas
    a través de las órdenes donde el usuario figura como subcoordinador.
    """
    # Obtener órdenes donde el usuario es subcoordinador
    ordenes = (
        OrdenTrabajo.objects
        .filter(equipos_asignados__subcoordinadores=request.user)
        .select_related('solicitud__colonia')
        .prefetch_related('solicitud__colonia__distritos')
        .order_by('-fecha_creacion')
    )

    colonias_map = {}
    total_relevamientos = 0
    # Contar todos los archivos subidos por el subcoordinador (usuario actual)
    total_archivos = ArchivoSubcoordinador.objects.filter(subido_por=request.user).count()
    ordenes_completadas = 0
    ordenes_en_proceso = 0
    
    for orden in ordenes:
        colonia = orden.solicitud.colonia if orden.solicitud else None
        if not colonia:
            continue
        
        # Contar relevamientos de esta orden
        relevamientos_count = Relevamiento.objects.filter(orden_trabajo=orden).count()
        total_relevamientos += relevamientos_count
        
        # Contar archivos subidos por cualquier usuario relacionados a la colonia (todas las órdenes)
        archivos_count_total = ArchivoSubcoordinador.objects.filter(orden_trabajo__solicitud__colonia=colonia).count()
        archivos_count_por_usuario = ArchivoSubcoordinador.objects.filter(orden_trabajo__solicitud__colonia=colonia, subido_por=request.user).count()

        # Obtener el archivo más reciente para la colonia (todas las órdenes) y últimos 3 archivos
        archivo_reciente = ArchivoSubcoordinador.objects.filter(orden_trabajo__solicitud__colonia=colonia).order_by('-fecha_subida').first()
        ultimos_archivos_qs = ArchivoSubcoordinador.objects.filter(orden_trabajo__solicitud__colonia=colonia).order_by('-fecha_subida')[:3]
        ultimos_archivos = [
            {
                'id': a.id,
                'nombre': a.nombre_archivo,
                'fecha_subida': a.fecha_subida,
                'subido_por': getattr(a.subido_por, 'username', None),
                'url': a.archivo.url if a.archivo else None,
            }
            for a in ultimos_archivos_qs
        ]
        
        # Contar estados de órdenes
        if orden.estado == 'completada':
            ordenes_completadas += 1
        elif orden.estado in ('en_proceso', 'asignada'):
            ordenes_en_proceso += 1
        
        # Usar la primera orden encontrada para la colonia
        if colonia.id not in colonias_map:
            colonias_map[colonia.id] = {
                'id': colonia.id,
                'nombre': colonia.nombre,
                'codigo': getattr(colonia, 'codigo', ''),
                'distrito': colonia.distritos.first() if colonia.distritos.exists() else None,
                'ultima_carga': archivo_reciente.fecha_subida if archivo_reciente else None,
                'archivo_url': archivo_reciente.archivo.url if archivo_reciente and archivo_reciente.archivo else None,
                'numero_orden': getattr(orden, 'numero_orden', ''),
                'fecha_inicio_planeada': getattr(orden, 'fecha_inicio_planeada', None),
                'fecha_fin_planeada': getattr(orden, 'fecha_fin_planeada', None),
                # Archivos precat subidos por digitalizador (si la solicitud existe)
                'precat_files': [] if not orden.solicitud else [
                    {
                        'id': a.id,
                        'nombre': getattr(a, 'archivo', None) and getattr(a, 'archivo').name.split('/')[-1] or getattr(a, 'observaciones', '')[:40],
                        'fecha_subida': a.fecha_subida,
                        'tipo': a.tipo_archivo,
                    }
                    for a in orden.solicitud.precat_archivos.all().order_by('-fecha_subida')
                ],
                'estado_orden': orden.estado,
                'relevamientos_count': relevamientos_count,
                'archivos_count_usuario': archivos_count_por_usuario,
                'archivos_count_total': archivos_count_total,
                'ultimos_archivos': ultimos_archivos,
                # habilitar_subida se controla por la orden (formulario_habilitado)
                'habilitar_subida': bool(orden.formulario_habilitado),
            }

    colonias = list(colonias_map.values())

    return render(request, 'relevamiento/subcoordinador_dashboard.html', {
        'colonias': colonias,
        'total_ordenes': ordenes.count(),
        'total_archivos': total_archivos,
        'ordenes_en_proceso': ordenes_en_proceso,
        'ordenes_completadas': ordenes_completadas,
        'total_relevamientos': total_relevamientos,
    })

@login_required
@require_POST
def subcoordinador_upload(request):
    """Recibe archivos comprimidos desde el subcoordinador y los guarda en MEDIA_ROOT/vivser_relevamiento/.
    Nombre: <departamento>_<distrito>_<colonia>_<fecha>.<extension>
    Extensiones permitidas: .zip, .rar, .7z, .tar, .tar.gz, .gz
    """
    
    file = request.FILES.get('archivo')
    colonia_id = request.POST.get('colonia_id')
    if not file or not colonia_id:
        return JsonResponse({'success': False, 'message': 'Faltan datos'}, status=400)

    # Extensiones permitidas
    extensiones_validas = ('.zip', '.rar', '.7z', '.tar', '.tar.gz', '.gz')
    filename_lower = file.name.lower()
    if not any(filename_lower.endswith(ext) for ext in extensiones_validas):
        return JsonResponse({'success': False, 'message': 'Solo se permiten archivos comprimidos (.zip, .rar, .7z, .tar, .tar.gz, .gz)'}, status=400)

    # Buscar la orden más reciente del subcoordinador para esa colonia
    orden = OrdenTrabajo.objects.filter(
        solicitud__colonia_id=colonia_id,
        equipos_asignados__subcoordinadores=request.user
    ).order_by('-fecha_creacion').first()

    if not orden:
        return JsonResponse({'success': False, 'message': 'No se encontró orden asociada o no tiene permisos'}, status=403)

    # Obtener datos geográficos
    colonia = orden.solicitud.colonia if orden.solicitud else None
    distrito = colonia.distritos.first() if colonia and colonia.distritos.exists() else None
    departamento = distrito.departamento if distrito else None
    
    # Construir nombre del archivo: departamento_distrito_colonia_fecha
    fecha_str = tz.now().strftime('%Y%m%d_%H%M%S')
    departamento_str = departamento.nombre.replace(' ', '_') if departamento else 'sin_depto'
    distrito_str = distrito.nombre.replace(' ', '_') if distrito else 'sin_distrito'
    colonia_str = colonia.nombre.replace(' ', '_') if colonia else f'colonia{colonia_id}'

    # Extraer extensión del archivo original
    original_ext = ''
    if file.name.lower().endswith('.tar.gz'):
        original_ext = '.tar.gz'
    else:
        original_ext = os.path.splitext(file.name)[1]

    # Construir nombre completo del archivo
    filename = f"{departamento_str}_{distrito_str}_{colonia_str}_{fecha_str}{original_ext}"
    # Sanitizar nombre: permitir solo letras, números, guiones, guiones bajos, puntos
    filename = re.sub(r'[^A-Za-z0-9_.\-]', '', filename)
    # Asegurar longitud máxima razonable (255 - para compatibilidad con FS/DB)
    if len(filename) > 250:
        name, ext = os.path.splitext(filename)
        filename = name[:250 - len(ext)] + ext
    
    # Guardar en la base de datos usando el modelo ArchivoSubcoordinador
    try:
        # Forzar que el archivo guarde con el nombre construido
        file.name = filename
        archivo_obj = ArchivoSubcoordinador(
            orden_trabajo=orden,
            archivo=file,
            nombre_archivo=filename,
            subido_por=request.user
        )
        archivo_obj.save()
        
        # También actualizar relevamientos existentes si los hay
        relevamientos = Relevamiento.objects.filter(orden_trabajo=orden)
        if relevamientos.exists():
            for rel in relevamientos:
                rel.archivo_subcoordinador = archivo_obj.archivo
                rel.fecha_subida_archivo = archivo_obj.fecha_subida
                rel.save(update_fields=['archivo_subcoordinador', 'fecha_subida_archivo'])
            mensaje = f'Archivo subido correctamente y vinculado a {relevamientos.count()} relevamiento(s)'
        else:
            mensaje = 'Archivo subido correctamente. Listo para vincular a relevamientos.'
            
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'Error al guardar archivo: {str(e)}'
        }, status=500)

    return JsonResponse({
        'success': True, 
        'message': mensaje,
        'filename': filename,
        'fecha_subida': archivo_obj.fecha_subida.strftime('%d/%m/%Y %H:%M')
    })

##################################
# DASHBOARD ENCUESTADOR
##################################
@login_required
@encuestador_required
def encuestador_dashboard(request):
    """
    Dashboard para encuestadores: muestra todas las órdenes de trabajo
    en las que el usuario está asignado como encuestador.
    """
    ordenes = (
        OrdenTrabajo.objects
        .exclude(estado__in=['reactivado', 'cancelada'])
        .filter(equipos_asignados__encuestadores=request.user)
        .distinct()
        .select_related(
            'solicitud',
            'solicitud__colonia',
            'coordinador_responsable',
        )
        .prefetch_related('equipos_asignados')
        .order_by('-fecha_creacion')
    )

    # Contar relevamientos propios por orden y calcular propiedades usadas en la plantilla
    relevamientos_por_orden = {}
    relevamientos_totales_por_orden = {}
    
    for orden in ordenes:
        # Relevamientos personales del encuestador
        relevamientos_por_orden[orden.pk] = Relevamiento.objects.filter(
            orden_trabajo=orden,
            encuestador=request.user,
        ).count()
        
        # Relevamientos totales de la colonia (todos los encuestadores)
        colonia = orden.solicitud.colonia if orden.solicitud else None
        if colonia:
            relevamientos_totales_por_orden[orden.pk] = Relevamiento.objects.filter(
                colonia=colonia
            ).count()
        else:
            relevamientos_totales_por_orden[orden.pk] = 0

    # Mapeo simple para badge/icon según estado
    estado_map = {
        'generada': {'badge': 'secondary', 'icon': 'fa-file-alt'},
        'asignada': {'badge': 'warning', 'icon': 'fa-user-check'},
        'en_proceso': {'badge': 'primary', 'icon': 'fa-spinner'},
        'completada': {'badge': 'success', 'icon': 'fa-check-circle'},
        'cancelada': {'badge': 'danger', 'icon': 'fa-times-circle'},
    }

    ordenes_context = []
    for orden in ordenes:
        m = estado_map.get(orden.estado, {'badge': 'secondary', 'icon': 'fa-circle'})
        cnt_personal = relevamientos_por_orden.get(orden.pk, 0)
        cnt_total = relevamientos_totales_por_orden.get(orden.pk, 0)
        meta = getattr(orden, 'meta_encuestas', 0) or 0
        # Calcular progreso basado en el total de la colonia
        progreso_percent = int(0 if meta == 0 else (cnt_total / meta) * 100)
        ordenes_context.append({
            'orden': orden,
            'estado_badge': m['badge'],
            'estado_icon': m['icon'],
            'relevamientos_count': cnt_personal,  # Encuestas personales
            'relevamientos_total': cnt_total,  # Encuestas totales de la colonia
            'meta_encuestas': meta,
            'progreso_percent': progreso_percent,
            'allow_new': orden.estado in ('asignada', 'en_proceso', 'generada') and orden.formulario_habilitado,
            'formulario_habilitado': orden.formulario_habilitado,
        })

    # Estadísticas rápidas
    total_ordenes = ordenes.count()
    en_proceso_count = sum(1 for o in ordenes if o.estado in ('en_proceso', 'asignada'))
    completadas_count = sum(1 for o in ordenes if o.estado == 'completada')
    total_relevamientos = sum(relevamientos_por_orden.values())

    context = {
        'ordenes': ordenes,  # mantener por compatibilidad si algo más lo usa
        'ordenes_context': ordenes_context,
        'relevamientos_por_orden': relevamientos_por_orden,
        'total_ordenes': total_ordenes,
        'en_proceso_count': en_proceso_count,
        'completadas_count': completadas_count,
        'total_relevamientos': total_relevamientos,
    }
    return render(request, 'relevamiento/encuestador_dashboard.html', context)

# Modos que ya tienen su propio wizard + resumen. Al migrar Servicio 
MODOS_WIZARD = ('ocupante', 'conflicto','servicio',)

# ─────────────────────────────────────────────
# UTILIDAD INTERNA: extraer datos geográficos
# de una OrdenTrabajo
# ─────────────────────────────────────────────

def datos_geograficos_desde_orden(orden):
    """
    Devuelve {colonia, distrito, departamento, distritos_count} desde la
    solicitud de la OT.

    - distrito/departamento solo se completan cuando la colonia tiene
      EXACTAMENTE un distrito. Si tiene 0 o 2+, se devuelven None: el
      encuestador es responsable de elegir (ver RelevamientoParte1Form,
      que muestra el select de distrito cuando distritos_count > 1).
    - distritos_count siempre se devuelve (0 si no hay colonia), útil en
      templates y en el form.
    """
    solicitud = orden.solicitud
    colonia = solicitud.colonia if solicitud else None

    distrito = None
    departamento = None
    distritos_count = 0

    if colonia:
        distritos = list(colonia.distritos.select_related('departamento'))
        distritos_count = len(distritos)
        if distritos_count == 1:
            distrito = distritos[0]
            departamento = distrito.departamento

    return {
        'colonia': colonia,
        'distrito': distrito,
        'departamento': departamento,
        'distritos_count': distritos_count,
    }

# ─────────────────────────────────────────────
# CUESTIONARIO OCUPANTE
# ─────────────────────────────────────────────
@login_required
@encuestador_required
def ocupante_parte1(request, orden_id):
    """
    PARTE 1 del wizard modo Ocupante: Datos Geográficos + Ocupante/Cónyuge.
    Al guardar, CREA el Relevamiento (borrador, estado_carga='parte_1') y
    redirige a la Parte 2 — ver continuar_encuesta().
    """
    orden = get_object_or_404(OrdenTrabajo, pk=orden_id)

    if not orden.formulario_habilitado:
        messages.warning(
            request,
            'El formulario de relevamiento no está habilitado. '
            'Contacte al coordinador de campo para habilitarlo.'
        )
        return redirect('relevamiento:encuestador_dashboard')

    datos_geo = datos_geograficos_desde_orden(orden)
    colonia = datos_geo['colonia']
    initial = {}

    if request.method == 'POST':
        form = RelevamientoParte1Form(
            request.POST, 
            colonia=colonia,
            initial=initial,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    relevamiento = form.save(commit=False)
                    relevamiento.colonia = datos_geo['colonia']
                    relevamiento.orden_trabajo = orden
                    relevamiento.encuestador = request.user
                    relevamiento.tipo_registro = 'ocupante'
                    relevamiento.estado_carga = 'parte_1'
                    relevamiento.save()
                    form.save_m2m()

                messages.success(request, 'Parte 1 guardada. Continuá con los datos del lote.')
                return redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='lote')
            except IntegrityError:
                form.add_error(
                    'manzana',
                    "Ya existe un relevamiento con esa manzana y lote en esta colonia."
                )
                messages.error(request, 'Ese lote ya fue registrado en esta colonia.')
            except Exception:
                logger.exception("Error creando relevamiento (ocupante) para OT %s", orden.pk)
                messages.error(request, 'Ocurrió un error inesperado. Contacte al administrador.')
        else:
            messages.error(request, 'Hay errores en el formulario. Revise los campos marcados.')
    else:
        form = RelevamientoParte1Form(
            colonia=colonia,
            initial=initial,
        )

    context = {
        'form': form,
        'orden': orden,
        'datos_geo': datos_geo,
        'title': f'Nueva Encuesta (Parte 1 de 4) — {orden}',
    }
    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/ocupante/cuestionario_ocupante_parte1.html',
        context,
    )

@login_required
@encuestador_required
def continuar_encuesta(request, pk, parte):
    relevamiento = get_object_or_404(Relevamiento, pk=pk)

    # Verificamos si el tipo de relevamiento tiene permitido entrar a esta vista
    es_ocupante = relevamiento.tipo_registro == 'ocupante'
    es_conflicto_o_servicio_en_resumen = (
        relevamiento.tipo_registro in ('conflicto', 'servicio') and parte == 'encuesta'
    )

    if not (es_ocupante or es_conflicto_o_servicio_en_resumen):
        messages.error(
            request,
            f'Este relevamiento es de tipo "{relevamiento.get_tipo_registro_display()}", '
            f'no del wizard de ocupante.'
        )
        return redirect('relevamiento:encuestador_dashboard')
    
    if relevamiento.encuestador_id != request.user.id and not request.user.is_superuser:
        messages.error(request, 'No tenés permiso para editar este relevamiento.')
        return redirect('relevamiento:encuestador_dashboard')

    if parte != 'encuesta':
        bloqueo = bloquear_si_completo(request, relevamiento)
        if bloqueo:
            return bloqueo

    if parte == 'lote':
        return continuar_parte2_lote(request, relevamiento)
    if parte == 'vivienda':
        return continuar_parte3_vivienda(request, relevamiento)
    if parte == 'productivos':
        return continuar_parte3_productivos(request, relevamiento)
    if parte == 'encuesta':
        return continuar_parte4_resumen(request, relevamiento)
    if parte == 'identificacion':
        return continuar_parte1_editar(request, relevamiento)

    messages.error(request, f'Parte "{parte}" no reconocida.')
    return redirect('relevamiento:encuestador_dashboard')
    
def continuar_parte2_lote(request, relevamiento):
    """PARTE 2: condición de vivienda + uso del lote. Define la ruta
    siguiente (Vivienda o Datos Productivos) según condicion_vivienda."""
    CAMPOS_RESIDENCIA = (
        'residencia_manzana', 'residencia_lote',
        'encargado_residencia', 'relacion_con_lote',
    )

    if request.method == 'POST':
        condicion_anterior = relevamiento.condicion_vivienda
        residencia_tenia_datos = any(
            getattr(relevamiento, f) for f in CAMPOS_RESIDENCIA
        )

        form = RelevamientoParte2Form(request.POST, instance=relevamiento)
        if form.is_valid():
            rel = form.save(commit=False)
            rel.condicion_encuestado = 'ocupante'
            condicion_nueva = rel.condicion_vivienda

            # ── Si reside en el lote, los datos de "otra residencia" no aplican ──
            if condicion_nueva == 'presente':
                for nombre in CAMPOS_RESIDENCIA:
                    setattr(rel, nombre, form.fields[nombre].empty_value)

            with transaction.atomic():
                rel.save()
                form.save_m2m()

                # ── Cascada: si pasó a sin_vivienda, borrar todo lo de vivienda ──
                if condicion_nueva == 'sin_vivienda':
                    tenia_datos = relevamiento.viviendas.exists()
                    relevamiento.viviendas.all().delete()
                    if tenia_datos:
                        messages.info(
                            request,
                            'Se eliminaron los datos de vivienda, equipamiento y población '
                            'porque la condición cambió a "sin vivienda".'
                        )
                    if condicion_nueva == 'presente' and residencia_tenia_datos:
                        messages.info(
                            request,
                            'Se eliminaron los datos de residencia '
                            'porque la condición cambió a "presente".'
                        )

            messages.success(request, 'Parte 2: "Datos del lote", guardado.')

            # Obtener si viene del resumen
            origen = request.POST.get('origen') or request.GET.get('origen')
            # Si cambió A presente desde el resumen (de cualquier valor anterior), ir a vivienda
            if origen == 'resumen' and condicion_anterior != condicion_nueva \
                    and condicion_nueva in ('presente', 'ausente', 'en_construccion', 'desocupada'):
                return redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='vivienda')
            # Si la nueva condición requiere vivienda (pero no es cambio desde sin_vivienda)
            if condicion_nueva in ('presente', 'ausente', 'en_construccion', 'desocupada'):
                return destino_tras_guardar(
                    request, relevamiento,
                    redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='vivienda')
                )
            
            # Si es sin_vivienda, ir a productivos
            return destino_tras_guardar(
                request, relevamiento,
                redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='productivos')
            )
        else:
            messages.error(request, 'Hay errores en el formulario. Revise los campos marcados.')
    else:
        form = RelevamientoParte2Form(instance=relevamiento)

    context = {
        'form': form,
        'relevamiento': relevamiento,
        'title': f'Encuesta #{relevamiento.pk} — Parte 2 de 4',
        'origen_resumen': request.GET.get('origen') == 'resumen',
    }
    
    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/ocupante/cuestionario_ocupante_parte2.html',
        context,
    )

class ErrorEnFormset(Exception):
    """Corta el guardado (y revierte la transacción) mostrando qué falló."""
    def __init__(self, detalle):
        super().__init__(' | '.join(detalle[:6]) or 'Datos inválidos.')

def resumen_errores(*items):
    """Junta los errores de forms y formsets en una lista legible."""
    lineas = []
    for item in items:
        if hasattr(item, 'forms'):  # formset
            nombre = item.prefix or item.__class__.__name__
            for err in item.non_form_errors():
                lineas.append(f'{nombre}: {err}')
            for i, f in enumerate(item.forms, 1):
                for campo, errs in f.errors.items():
                    lineas.append(f'{nombre} #{i} · {campo}: {" ".join(errs)}')
        else:
            for campo, errs in item.errors.items():
                lineas.append(f'{campo}: {" ".join(errs)}')
    return lineas

def avisar_errores(request, *items):
    mensaje = 'Hay errores en el formulario.'
    detalle = resumen_errores(*items)
    if detalle:
        mensaje += ' ' + ' | '.join(detalle[:6])
    messages.error(request, mensaje)

def continuar_parte3_vivienda(request, relevamiento):
    """PARTE 3 (Ruta 1): Vivienda + Equipamiento + Población.
    Solo se llega acá si condicion_vivienda ∈ {presente, ausente,
    en_construccion, desocupada} (lo decide _continuar_parte2_lote)."""

    ViviendaFS = inlineformset_factory(
        Relevamiento, Vivienda, form=ViviendaForm, extra=0, can_delete=True, fk_name='relevamiento'
    )
    MiembroFS = inlineformset_factory(
        Vivienda, Miembro, form=MiembroForm, extra=0, can_delete=True, fk_name='vivienda'
    )
    InstitucionFS = inlineformset_factory(
        Relevamiento, InstitucionEnLote, form=InstitucionEnLoteForm, extra=0, can_delete=True, fk_name='relevamiento'
    )

    if request.method == 'POST':
        vivienda_formset = ViviendaFS(request.POST, instance=relevamiento, prefix='viviendas')
        institucion_formset = InstitucionFS(request.POST, instance=relevamiento, prefix='instituciones')

        if vivienda_formset.is_valid() and institucion_formset.is_valid():
            try:
                with transaction.atomic():
                    viviendas_guardadas = []
                    numero_actual = 1
                    for i, viv_form in enumerate(vivienda_formset):
                        if viv_form.cleaned_data.get('DELETE', False):
                            if viv_form.instance.pk:
                                viv_form.instance.delete()
                            continue
                        if viv_form.cleaned_data:
                            vivienda = viv_form.save(commit=False)
                            vivienda.relevamiento = relevamiento
                            vivienda.numero = numero_actual
                            numero_actual += 1
                            viviendas_guardadas.append((i, vivienda, viv_form))

                    principales = [v for _, v, _ in viviendas_guardadas if v.es_principal]
                    if not principales and viviendas_guardadas:
                        viviendas_guardadas[0][1].es_principal = True
                    elif len(principales) > 1:
                        for vivienda in principales[1:]:
                            vivienda.es_principal = False

                    for i, vivienda, viv_form in viviendas_guardadas:
                        vivienda.save()
                        viv_form.save_m2m()

                        miem_prefix = f'miembros_viv_{i}'
                        miem_fs = MiembroFS(request.POST, instance=vivienda, prefix=miem_prefix)

                        if not miem_fs.is_valid():
                            raise ErrorEnFormset(resumen_errores(miem_fs))

                        miembros = miem_fs.save(commit=False)
                        for miembro in miembros:
                            miembro.relevamiento = relevamiento
                            miembro.save()
                        for obj in miem_fs.deleted_objects:
                            obj.delete()
                        miem_fs.save_m2m()

                    institucion_formset.save()

                    relevamiento.estado_carga = 'parte_3'
                    relevamiento.save(update_fields=['estado_carga'])

                messages.success(request, 'Vivienda y población guardadas.')
                return destino_tras_guardar(
                    request, relevamiento,
                    redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='productivos')
                )
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
             avisar_errores(request, vivienda_formset, institucion_formset)
    else:
        vivienda_formset = ViviendaFS(instance=relevamiento, prefix='viviendas')
        institucion_formset = InstitucionFS(instance=relevamiento, prefix='instituciones')

    vivienda_miembro_formsets = {}
    for i, viv_form in enumerate(vivienda_formset.forms):
        miem_prefix = f'miembros_viv_{i}'
        if request.method == 'POST' and f'{miem_prefix}-TOTAL_FORMS' in request.POST:
            vivienda_miembro_formsets[i] = MiembroFS(request.POST, prefix=miem_prefix)
        elif viv_form.instance.pk:
            vivienda_miembro_formsets[i] = MiembroFS(instance=viv_form.instance, prefix=miem_prefix)
        else:
            vivienda_miembro_formsets[i] = MiembroFS(prefix=miem_prefix)

    miembro_template_formset = MiembroFS(prefix='miembros_viv_0')

    context = {
        'relevamiento': relevamiento,
        'vivienda_formset': vivienda_formset,
        'vivienda_miembro_formsets': vivienda_miembro_formsets,
        'miembro_template_formset': miembro_template_formset,
        'institucion_formset': institucion_formset,
        'mostrar_poblacion': relevamiento.condicion_vivienda in ('presente', 'ausente'),
        'title': f'Encuesta #{relevamiento.pk} — Parte 3 de 4',
        'origen_resumen': request.GET.get('origen') == 'resumen',
    }
    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/ocupante/cuestionario_ocupante_parte3_vivienda.html',
        context,
    )

def continuar_parte3_productivos(request, relevamiento):
    """PARTE 3 (común a Ruta 1 y Ruta 2): Cultivos + Ganadería + Mejoras."""

    CultivoFS = inlineformset_factory(
        Relevamiento, Cultivo, form=CultivoForm, extra=0, can_delete=True, fk_name='relevamiento'
    )
    GanaderiaFS = inlineformset_factory(
        Relevamiento, ProduccionGanadera, form=ProduccionGanaderaForm, extra=0, can_delete=True, fk_name='relevamiento'
    )

    if request.method == 'POST':
        mejoras_formset = RelevamientoMejorasForm(request.POST, instance=relevamiento)
        cultivo_formset = CultivoFS(request.POST, instance=relevamiento, prefix='cultivos')
        ganaderia_formset = GanaderiaFS(request.POST, instance=relevamiento, prefix='ganaderia')

        form_cierre = RelevamientoCierreForm(request.POST, instance=relevamiento)

        if mejoras_formset.is_valid() and cultivo_formset.is_valid() and ganaderia_formset.is_valid() and form_cierre.is_valid():
            try:
                with transaction.atomic():
                    rel = mejoras_formset.save(commit=False)
                    rel.estado_carga = 'parte_3'
                    rel.save()
                    mejoras_formset.save_m2m()
                    cultivo_formset.save()
                    ganaderia_formset.save()
                    form_cierre.save()

                messages.success(request, 'Datos productivos y mejoras guardados.')
                return destino_tras_guardar(
                    request, relevamiento,
                    redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='encuesta')
                )
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            avisar_errores(request, mejoras_formset, cultivo_formset, ganaderia_formset, form_cierre)
    else:
        mejoras_formset = RelevamientoMejorasForm(instance=relevamiento)
        cultivo_formset = CultivoFS(instance=relevamiento, prefix='cultivos')
        ganaderia_formset = GanaderiaFS(instance=relevamiento, prefix='ganaderia')
        form_cierre = RelevamientoCierreForm(instance=relevamiento)

    context = {
        'relevamiento': relevamiento,
        'mejoras_formset': mejoras_formset,
        'cultivo_formset': cultivo_formset,
        'ganaderia_formset': ganaderia_formset,
        'form_cierre': form_cierre,
        'title': f'Encuesta #{relevamiento.pk} — Parte 3 de 4',
        'origen_resumen': request.GET.get('origen') == 'resumen',
    }
    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/ocupante/cuestionario_ocupante_parte3_productivos.html',
        context,
    )

def continuar_parte1_editar(request, relevamiento):
    """Edición de los datos de la Parte 1 (identificación/ocupante) para
    un Relevamiento YA creado. Se usa desde el lápiz 'Editar' del resumen."""
    orden = relevamiento.orden_trabajo
    datos_geo = datos_geograficos_desde_orden(orden)
    colonia = datos_geo['colonia']

    if request.method == 'POST':
        form = RelevamientoParte1Form(
            request.POST, 
            colonia=colonia,
            instance=relevamiento
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    rel = form.save(commit=False)
                    rel.save()
                    form.save_m2m()

                messages.success(request, 'Datos actualizados.')
                return destino_tras_guardar(
                    request, relevamiento,
                    redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='lote')
                )
            except IntegrityError:
                form.add_error(
                    'manzana',
                    "Ya existe otro relevamiento con esa manzana y lote en esta colonia."
                )
                messages.error(request, 'Ese lote ya está registrado en esta colonia.')
            except Exception:
                logger.exception("Error editando parte1 del relevamiento %s", relevamiento.pk)
                messages.error(request, 'Ocurrió un error inesperado. Contacte al administrador.')
        else:
            messages.error(request, 'Hay errores en el formulario. Revise los campos marcados.')
    else:
        form = RelevamientoParte1Form(
            colonia=colonia,
            instance=relevamiento)

    context = {
        'form': form,
        'orden': orden,
        'datos_geo': datos_geo,
        'origen_resumen': request.GET.get('origen') == 'resumen',
        'title': f'Encuesta #{relevamiento.pk} — Editar identificación',
    }
    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/ocupante/cuestionario_ocupante_parte1.html',
        context,
    )

def _nombre_usuario(usuario):
    if not usuario:
        return None
    return usuario.get_full_name() or usuario.username

def _items(*pares):
    """Devuelve solo los pares (etiqueta, valor) que tienen algo cargado."""
    return [(etiqueta, valor) for etiqueta, valor in pares if valor not in (None, '', [], ())]

def _etiquetas(claves, choices):
    """['galpon', 'pozo'] -> 'Galpón, Pozo' usando las choices del modelo."""
    mapa = dict(choices)
    return ', '.join(mapa.get(c, c) for c in (claves or []))

def meta_seccion(titulo):
    """Devuelve (icono_fa, tono) para una sección según su título."""
    t = titulo.lower()
    if t.startswith('lote'):                    return ('fa-map-marker-alt', 'blue')
    if t.startswith('ocupante'):                return ('fa-user', 'teal')
    if t.startswith('cónyuge'):                 return ('fa-heart', 'rose')
    if t.startswith('condición'):               return ('fa-house-circle-check', 'amber')
    if t.startswith('vivienda'):                return ('fa-house-chimney', 'green')
    if t.startswith('instituciones'):           return ('fa-building-columns', 'purple')
    if t.startswith('producción'):              return ('fa-seedling', 'orange')
    if t.startswith('pretendiente'):            return ('fa-scale-balanced', 'amber')
    if t.startswith('responsable'):             return ('fa-user-tie', 'teal')
    if t.startswith('uso del lote'):            return ('fa-layer-group', 'amber')
    if t.startswith('mejoras'):                 return ('fa-screwdriver-wrench', 'orange')
    if t.startswith('cierre'):                  return ('fa-flag-checkered', 'green')

    return ('fa-circle-dot', 'slate')

def _describir_vivienda(v):
    partes = [
        v.get_paredes_display() if v.paredes else '',
        v.get_piso_display() if v.piso else '',
        v.get_techo_display() if v.techo else '',
        f'{v.piezas} piezas' if v.piezas else '',
    ]
    return ', '.join(p for p in partes if p)

def continuar_parte4_resumen(request, relevamiento):
    """PARTE 4: resumen final. Antes de confirmar muestra el botón de cierre;
    después de confirmar es la pantalla definitiva (Nueva encuesta / Fotos)."""
    
    r = relevamiento
    orden = r.orden_trabajo
    # ── POST: confirmar y finalizar ─────────────────────────────────
    if request.method == 'POST' and r.estado_carga != 'completo':
        r.estado_carga = 'completo'
        r.fecha_de_encuesta = timezone.now()
        r.save(update_fields=['estado_carga', 'fecha_de_encuesta'])

        messages.success(
            request,
            f'Relevamiento #{r.pk} confirmado y finalizado correctamente.'
        )
        return redirect(
            'relevamiento:continuar_encuesta',
            pk=r.pk, parte='encuesta'
        )

    # ── Equipo ──────────────────────────────────────────────────────────
    equipo = (
        orden.equipos_asignados.filter(encuestadores=r.encuestador).first()
        or orden.equipos_asignados.first()
    )
    coordinador = _nombre_usuario(equipo.coordinador_campo) if equipo else None
    subcoordinadores = [_nombre_usuario(u) for u in equipo.subcoordinadores.all()] if equipo else []
    if not subcoordinadores:
        subcoordinadores = [_nombre_usuario(u) for u in orden.solicitud.subcoordinadores.all()]

    # ── Secciones: asegurando que guarde correctamente la clave 'editar' ──
    secciones = []

    def agregar(titulo, editar, items):
        if items:
            icon, tone = meta_seccion(titulo)
            secciones.append({
                'titulo': titulo, 
                'editar': editar, 
                'items': items,
                'icon': icon,
                'tone': tone,
            })

    agregar('Lote', 'identificacion', _items(
        ('Manzana', r.manzana), ('Lote', r.lote_indert), ('Dimensión', r.dimensiones),
        ('Superficie (ha)', r.superficie_ha),
        ('Tipo', r.get_tipo_lote_display() if r.tipo_lote else ''),
    ))
    agregar('Ocupante', 'identificacion', _items(
        ('Nombre', r.quien_es_el_ocupante), ('CI', r.cedula_ocupante),
        ('Sexo', r.get_sexo_ocupante_display() if r.sexo_ocupante else ''),
        ('Estado civil', r.get_estado_civil_ocupante_display() if r.estado_civil_ocupante else ''),
        ('Telefono', r.telefono_ocupante or ''),
    ))
    if r.quien_es_el_conyuge:
        agregar('Cónyuge', 'identificacion', _items(
            ('Nombre', r.quien_es_el_conyuge), ('CI', r.cedula_conyuge),
            ('Sexo', r.get_sexo_conyuge_display() if r.sexo_conyuge else ''),
            ('Estado civil', r.get_estado_civil_conyuge_display() if r.estado_civil_conyuge else ''),
        ))
    agregar('Condición del lote', 'lote', _items(
        ('Condición de vivienda', r.get_condicion_vivienda_display()),
        ('Residencia · manzana', r.residencia_manzana), ('Residencia · lote', r.residencia_lote),
        ('Encargado', r.encargado_residencia), ('Parentesco', r.relacion_con_lote),
        ('Uso del lote', _etiquetas(r.uso_lote_ocupante, USO_LOTE_OCUPANTE_CHOICES)),
    ))

    for v in r.viviendas.all().order_by('numero'):
        mapa_relacion = dict(RELACION_CON_LOTE_CHOICES)
        poblacion = '; '.join(
            f'{m.nombre_miembro} ({mapa_relacion.get(m.relacion_con_lote, m.relacion_con_lote)})' if m.relacion_con_lote else m.nombre_miembro
            for m in v.miembros.all()
        )
        agregar(
            f'Vivienda {v.numero}' + (' · principal' if v.es_principal else ''), 'vivienda',
            _items(
                ('Paredes', v.get_paredes_display() if v.paredes else ''),
                ('Piso', v.get_piso_display() if v.piso else ''),
                ('Techo', v.get_techo_display() if v.techo else ''),
                ('Piezas', v.piezas),
                ('Agua', v.get_agua_proviene_display() if v.agua_proviene else ''),
                ('Baño', v.get_tipo_bano_display() if v.tipo_bano else ''),
                ('Equipamiento', _etiquetas(v.equipamientos, EQUIPAMIENTOS_CHOICES)),
                ('Población', poblacion),
            ),
        )
    agregar('Producción e infraestructura', 'productivos', _items(
        ('Cultivos', '; '.join(f'{c.get_tipo_cultivo_display()} · {c.hectareas} ha' for c in r.cultivos.all())),
        ('Ganadería', '; '.join(f'{g.get_tipo_ganaderia_display()} × {g.cantidad}' for g in r.producciones_ganaderas.all())),
        ('Mejoras', _etiquetas(r.mejoras, MEJORAS_CHOICES)),
    ))
    agregar('Instituciones / servicios', 'vivienda', _items(
        ('Registradas', ', '.join(i.nombre_servicio for i in r.instituciones.all())),
    ))
    agregar('Cierre de la encuesta', 'cierre', _items(
        ('Estado de la entrevista', r.get_estado_entrevista_display() if r.estado_entrevista else ''),
        ('Firmó solicitud', 'Sí' if r.firmo_solicitud else 'No'),
        ('Observaciones', r.observacion_encuesta),
    ))

    if r.tipo_registro == 'conflicto':
        secciones = secciones_conflicto(r)
    if r.tipo_registro == 'servicio':
            secciones = secciones_servicio(r)
        
    context = {
        'relevamiento': r,
        'orden': orden,
        'coordinador': coordinador,
        'subcoordinadores': subcoordinadores,
        'secciones': secciones,
        'completo': r.estado_carga == 'completo',
        'cantidad_fotos': r.fotos.count(),
        'title': f'Encuesta #{r.pk} — Resumen',
    }
    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/ocupante/cuestionario_ocupante_parte4_resumen.html',
        context,
    )

def secciones_conflicto(r):
    """Secciones del resumen para el modo Conflicto. Cada una trae su propia
    URL de edición (el lápiz del template)."""

    def url(parte):
        return reverse('relevamiento:continuar_conflicto', kwargs={'pk': r.pk, 'parte': parte})

    secciones = []

    def agregar(titulo, destino, items):
        if items:
            icon, tone = meta_seccion(titulo)
            secciones.append({'titulo': titulo, 'url': destino, 'items': items, 'icon': icon, 'tone': tone})

    agregar('Lote', url('lote'), _items(
        ('Manzana', r.manzana), ('Lote', r.lote_indert), ('Dimensión', r.dimensiones),
        ('Superficie (ha)', r.superficie_ha),
        ('Tipo', r.get_tipo_lote_display() if r.tipo_lote else ''),
    ))

    for n, p in enumerate(r.pretendientes.all().order_by('pk'), start=1):
        agregar(f'Pretendiente {n} · {p.nombre_pretendiente}', url('pretendientes'), _items(
            ('CI', p.ci_pretendiente),
            ('Estado civil', p.get_estado_civil_pretendiente_display() if p.estado_civil_pretendiente else ''),
            ('Relación con el ocupante', p.relacion_con_lote),
            ('Condición de vivienda', p.get_condicion_vivienda_display() if p.condicion_vivienda else ''),
            ('Vivienda', '; '.join(_describir_vivienda(v) for v in p.viviendas.all())),
            ('Población', '; '.join(
                f'{m.nombre_miembro} ({m.relacion_con_lote})' if m.relacion_con_lote else m.nombre_miembro
                for m in p.miembros.all()
            )),
            ('Cultivos', '; '.join(f'{c.get_tipo_cultivo_display()} · {c.hectareas} ha' for c in p.cultivos.all())),
            ('Ganadería', '; '.join(f'{g.get_tipo_ganaderia_display()} × {g.cantidad}' for g in p.producciones_ganaderas.all())),
            ('Mejoras', _etiquetas(p.mejoras, MEJORAS_CHOICES)),
            ('Observaciones', p.observaciones),
        ))

    agregar('Instituciones', url('instituciones'), _items(
        ('Instituciones', ', '.join(i.nombre_servicio for i in r.instituciones.all())),
    ))
    agregar('Cierre de la encuesta', url('pretendientes'), _items(
        ('Estado de la entrevista', r.get_estado_entrevista_display() if r.estado_entrevista else ''),
        ('Firmó solicitud', 'Sí' if r.firmo_solicitud else 'No'),
        ('Observaciones', r.observacion_encuesta),
    ))

    return secciones

def secciones_servicio(r):
    """Secciones del resumen para el modo Servicio."""

    def url(parte):
        return reverse('relevamiento:continuar_servicio', kwargs={'pk': r.pk, 'parte': parte})

    secciones = []

    def agregar(titulo, destino, items):
        if items:
            icon, tone = meta_seccion(titulo)
            secciones.append({'titulo': titulo, 'url': destino, 'items': items, 'icon': icon, 'tone': tone})

    agregar('Lote', url('lote'), _items(
        ('Manzana', r.manzana), ('Lote', r.lote_indert), ('Dimensión', r.dimensiones),
        ('Superficie (ha)', r.superficie_ha),
        ('Tipo', r.get_tipo_lote_display() if r.tipo_lote else ''),
    ))
    agregar('Instituciones / servicios', url('lote'), _items(
        ('Registradas', ', '.join(i.nombre_servicio for i in r.instituciones.all())),
    ))
    agregar('Responsable', url('lote'), _items(
        ('Nombre', r.quien_es_el_ocupante), ('CI', r.cedula_ocupante),
        ('Sexo', r.get_sexo_ocupante_display() if r.sexo_ocupante else ''),
        ('Estado civil', r.get_estado_civil_ocupante_display() if r.estado_civil_ocupante else ''),
        ('Telefono', r.telefono_ocupante or ''),
    ))
    agregar('Uso del lote', url('lote'), _items(
        ('Uso', _etiquetas(r.uso_lote_servicio, USO_LOTE_SERVICIO_CHOICES)),
    ))
    agregar('Mejoras e infraestructura', url('lote'), _items(
        ('Mejoras', _etiquetas(r.mejoras, MEJORAS_CHOICES)),
    ))
    agregar('Cierre de la encuesta', url('lote'), _items(
        ('Estado de la entrevista', r.get_estado_entrevista_display() if r.estado_entrevista else ''),
        ('Firmó solicitud', 'Sí' if r.firmo_solicitud else 'No'),
        ('Observaciones', r.observacion_encuesta),
    ))

    return secciones

def destino_tras_guardar(request, relevamiento, destino_normal):
    """Si esta parte se abrió desde el resumen final (vía el lápiz de
    'Editar', que agrega ?origen=resumen) y el usuario la completa, lo
    mandamos de vuelta al resumen en vez de seguir avanzando por el wizard.
    Si no, sigue el flujo normal (Parte 1 → 2 → 3 → 4).
    Si forzar_vivienda=True, va a vivienda aunque sea del resumen."""
    origen = request.POST.get('origen') or request.GET.get('origen')
    if origen == 'resumen':
        return redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='encuesta')
    return destino_normal

# ─────────────────────────────────────────────
# MODO CONFLICTO
# ─────────────────────────────────────────────
@login_required
@encuestador_required
def conflicto_datos_lote(request, orden_id):
    """CONFLICTO – Parte 1: datos del lote. Crea el Relevamiento (borrador)
    y sigue a la pantalla de pretendientes."""
    orden = get_object_or_404(OrdenTrabajo, pk=orden_id)

    if not orden.formulario_habilitado:
        messages.warning(
            request,
            'El formulario de relevamiento no está habilitado. '
            'Contacte al coordinador de campo para habilitarlo.'
        )
        return redirect('relevamiento:encuestador_dashboard')

    datos_geo = datos_geograficos_desde_orden(orden)
    colonia = datos_geo['colonia']

    initial = {
        'distrito': datos_geo['distrito'],
    }

    if request.method == 'POST':
        form = RelevamientoConflictoParte1Form(
            request.POST,
            colonia=colonia,
            initial=initial,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    rel = form.save(commit=False)
                    rel.colonia = datos_geo['colonia']
                    rel.orden_trabajo = orden
                    rel.encuestador = request.user
                    rel.tipo_registro = 'conflicto'
                    rel.estado_carga = 'parte_1'
                    rel.save()
                    form.save_m2m()
                messages.success(request, 'Datos del lote guardados. Continuá con los pretendientes.')
                return redirect('relevamiento:continuar_conflicto', pk=rel.pk, parte='pretendientes')
            except IntegrityError:
                form.add_error(
                    'manzana',
                    "Ya existe un relevamiento con esa manzana y lote en esta colonia."
                )
                messages.error(request, 'Ese lote ya fue registrado en esta colonia.')
            except Exception:
                logger.exception("Error creando relevamiento (conflicto) para OT %s", orden.pk)
                messages.error(request, 'Ocurrió un error inesperado. Contacte al administrador.')
        else:
            messages.error(request, 'Hay errores en el formulario. Revise los campos marcados.')
    else:
        form = RelevamientoConflictoParte1Form(
            colonia=colonia,
            initial=initial,
        )

    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/conflicto/cuestionario_conflicto_datos_lote.html',
        {
            'form': form,
            'orden': orden,
            'datos_geo': datos_geo,
            'title': f'Nueva Encuesta (Conflicto) — {orden}',
        },
    )

@login_required
@encuestador_required
def continuar_conflicto(request, pk, parte):
    relevamiento, bloqueo = conflicto_editable(request, pk)
    if bloqueo:
        return bloqueo

    if parte == 'pretendientes':
        return conflicto_pretendientes_e_instituciones(request, relevamiento)
    if parte == 'lote':
        return conflicto_editar_lote(request, relevamiento)
    if parte == 'instituciones':
        # Compatibilidad con el lápiz del resumen
        url = reverse('relevamiento:continuar_conflicto', kwargs={'pk': pk, 'parte': 'pretendientes'})
        return redirect(f'{url}?abrir_modal=1')

    messages.error(request, f'Parte "{parte}" no reconocida.')
    return redirect('relevamiento:encuestador_dashboard')

def conflicto_pretendientes_e_instituciones(request, rel):
    InstitucionFS = inlineformset_factory(
        Relevamiento, InstitucionEnLote, form=InstitucionEnLoteForm,
        extra=0, can_delete=True, fk_name='relevamiento'
    )

    if request.method == 'POST':
        form = RelevamientoCierreForm(request.POST, instance=rel)
        institucion_formset = InstitucionFS(request.POST, instance=rel, prefix='instituciones')

        if form.is_valid() and institucion_formset.is_valid():
            try:
                with transaction.atomic():
                    obj = form.save(commit=False)
                    obj.estado_carga = 'parte_4'
                    obj.save()
                    institucion_formset.save()
                messages.success(request, 'Datos guardados. Revisá el resumen y confirmá.')
                return redirect('relevamiento:continuar_encuesta', pk=rel.pk, parte='encuesta')
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            avisar_errores(request, form, institucion_formset)
    else:
        form = RelevamientoCierreForm(instance=rel)
        institucion_formset = InstitucionFS(instance=rel, prefix='instituciones')

    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/conflicto/cuestionario_conflicto.html',
        {
            'relevamiento': rel,
            'orden': rel.orden_trabajo,
            'pretendientes': rel.pretendientes.all().order_by('pk'),
            'form': form,
            'institucion_formset': institucion_formset,
            'puede_volver_al_resumen': rel.estado_carga == 'parte_4',
            'abrir_modal': request.GET.get('abrir_modal') == '1',
            'title': f'Encuesta #{rel.pk} (Conflicto) — Pretendientes',
        },
    )

@login_required
@encuestador_required
def pretendiente_vivienda(request, pk, pret_id):
    """CONFLICTO vivienda + equipamiento + población de UN pretendiente."""
    rel, bloqueo = conflicto_editable(request, pk)
    if bloqueo:
        return bloqueo
    pret = get_object_or_404(Pretendiente, pk=pret_id, relevamiento=rel)

    if pret.condicion_vivienda == 'sin_vivienda':
        messages.info(request, 'Este pretendiente no tiene vivienda: pasamos directo a producción.')
        return redirect('relevamiento:pretendiente_produccion', pk=rel.pk, pret_id=pret.pk)

    ViviendaFS = inlineformset_factory(
        Pretendiente, Vivienda, form=ViviendaForm, extra=0, can_delete=True, fk_name='pretendiente'
    )
    MiembroFS = inlineformset_factory(
        Vivienda, Miembro, form=MiembroForm, extra=0, can_delete=True, fk_name='vivienda'
    )

    if request.method == 'POST':
        vivienda_formset = ViviendaFS(request.POST, instance=pret, prefix='viviendas')

        if vivienda_formset.is_valid():
            try:
                with transaction.atomic():
                    viviendas_guardadas = []
                    numero_actual = 1
                    for i, viv_form in enumerate(vivienda_formset):
                        if viv_form.cleaned_data.get('DELETE', False):
                            if viv_form.instance.pk:
                                viv_form.instance.delete()
                            continue
                        if viv_form.cleaned_data:
                            vivienda = viv_form.save(commit=False)
                            vivienda.pretendiente = pret
                            vivienda.numero = numero_actual
                            numero_actual += 1
                            viviendas_guardadas.append((i, vivienda, viv_form))

                    principales = [v for _, v, _ in viviendas_guardadas if v.es_principal]
                    if not principales and viviendas_guardadas:
                        viviendas_guardadas[0][1].es_principal = True
                    elif len(principales) > 1:
                        for vivienda in principales[1:]:
                            vivienda.es_principal = False

                    for i, vivienda, viv_form in viviendas_guardadas:
                        vivienda.save()
                        viv_form.save_m2m()

                        miem_fs = MiembroFS(request.POST, instance=vivienda, prefix=f'miembros_viv_{i}')
                        if not miem_fs.is_valid():
                            raise ErrorEnFormset(resumen_errores(miem_fs))

                        for miembro in miem_fs.save(commit=False):
                            miembro.pretendiente = pret
                            miembro.relevamiento = rel
                            miembro.save()
                        for obj in miem_fs.deleted_objects:
                            obj.delete()
                        miem_fs.save_m2m()

                messages.success(request, 'Vivienda y población guardadas.')
                return redirect('relevamiento:pretendiente_produccion', pk=rel.pk, pret_id=pret.pk)
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            avisar_errores(request, vivienda_formset)
    else:
        vivienda_formset = ViviendaFS(instance=pret, prefix='viviendas')

    vivienda_miembro_formsets = {}
    for i, viv_form in enumerate(vivienda_formset.forms):
        miem_prefix = f'miembros_viv_{i}'
        if request.method == 'POST' and f'{miem_prefix}-TOTAL_FORMS' in request.POST:
            vivienda_miembro_formsets[i] = MiembroFS(request.POST, prefix=miem_prefix)
        elif viv_form.instance.pk:
            vivienda_miembro_formsets[i] = MiembroFS(instance=viv_form.instance, prefix=miem_prefix)
        else:
            vivienda_miembro_formsets[i] = MiembroFS(prefix=miem_prefix)

    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/conflicto/cuestionario_conflicto_pretendiente_vivienda.html',
        {
            'relevamiento': rel,
            'pretendiente': pret,
            'vivienda_formset': vivienda_formset,
            'vivienda_miembro_formsets': vivienda_miembro_formsets,
            'miembro_template_formset': MiembroFS(prefix='miembros_viv_0'),
            'mostrar_poblacion': pret.condicion_vivienda in ('presente', 'ausente'),
            'etiqueta_titular': 'pretendiente',
            'title': f'Encuesta #{rel.pk} (Conflicto) — Vivienda de {pret.nombre_pretendiente}',
        },
    )

@login_required
@encuestador_required
def pretendiente_produccion(request, pk, pret_id):
    """CONFLICTO cultivos, ganadería y mejoras de UN pretendiente."""
    rel, bloqueo = conflicto_editable(request, pk)
    if bloqueo:
        return bloqueo
    pret = get_object_or_404(Pretendiente, pk=pret_id, relevamiento=rel)

    CultivoFS = inlineformset_factory(
        Pretendiente, Cultivo, form=CultivoForm, extra=0, can_delete=True, fk_name='pretendiente'
    )
    GanaderiaFS = inlineformset_factory(
        Pretendiente, ProduccionGanadera, form=ProduccionGanaderaForm, extra=0, can_delete=True, fk_name='pretendiente'
    )

    if request.method == 'POST':
        form = PretendienteMejorasForm(request.POST, instance=pret)
        cultivo_formset = CultivoFS(request.POST, instance=pret, prefix='cultivos')
        ganaderia_formset = GanaderiaFS(request.POST, instance=pret, prefix='ganaderia')

        if form.is_valid() and cultivo_formset.is_valid() and ganaderia_formset.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    cultivo_formset.save()
                    ganaderia_formset.save()
                messages.success(request, f'Producción de {pret.nombre_pretendiente} guardada.')
                return redirect('relevamiento:continuar_conflicto', pk=rel.pk, parte='pretendientes')
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
             avisar_errores(request, form, cultivo_formset, ganaderia_formset)
    else:
        form = PretendienteMejorasForm(instance=pret)
        cultivo_formset = CultivoFS(instance=pret, prefix='cultivos')
        ganaderia_formset = GanaderiaFS(instance=pret, prefix='ganaderia')

    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/conflicto/cuestionario_conflicto_pretendiente_produccion.html',
        {
            'relevamiento': rel,
            'pretendiente': pret,
            'form': form,
            'cultivo_formset': cultivo_formset,
            'ganaderia_formset': ganaderia_formset,
            'title': f'Encuesta #{rel.pk} (Conflicto) — Producción de {pret.nombre_pretendiente}',
        },
    )

@login_required
@encuestador_required
def pretendiente_editar(request, pk, pret_id=None):
    """Alta (pret_id=None) o edición de la identificación de un pretendiente."""
    rel, bloqueo = conflicto_editable(request, pk)
    if bloqueo:
        return bloqueo
    pret = get_object_or_404(Pretendiente, pk=pret_id, relevamiento=rel) if pret_id else None

    if request.method == 'POST':
        form = PretendienteIdentificacionForm(request.POST, instance=pret)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.relevamiento = rel
            obj.save()
            if rel.estado_carga == 'parte_1':
                rel.estado_carga = 'parte_2'
                rel.save(update_fields=['estado_carga'])
            messages.success(request, f'Pretendiente {obj.nombre_pretendiente} guardado.')
            # pretendiente_editar, caso exitoso:
            if obj.condicion_vivienda == 'sin_vivienda':
                return redirect('relevamiento:pretendiente_produccion', pk=rel.pk, pret_id=obj.pk)
            return redirect('relevamiento:pretendiente_vivienda', pk=rel.pk, pret_id=obj.pk)
        messages.error(request, 'Hay errores en el formulario. Revise los campos marcados.')
    else:
        form = PretendienteIdentificacionForm(instance=pret)

    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/conflicto/cuestionario_conflicto_pretendiente.html',
        {
            'form': form,
            'relevamiento': rel,
            'pretendiente': pret,
            'title': f'Encuesta #{rel.pk} (Conflicto) — Pretendiente',
        },
    )

@login_required
@encuestador_required
@require_POST
def pretendiente_eliminar(request, pk, pret_id):
    rel, bloqueo = conflicto_editable(request, pk)
    if bloqueo:
        return bloqueo
    pret = get_object_or_404(Pretendiente, pk=pret_id, relevamiento=rel)
    nombre = pret.nombre_pretendiente
    pret.delete()  # CASCADE borra su vivienda, miembros, cultivos, etc.
    messages.success(request, f'Pretendiente {nombre} eliminado.')
    return redirect('relevamiento:continuar_conflicto', pk=rel.pk, parte='pretendientes')

def relevamiento_editable(request, pk, tipo):
    """(rel, None) si se puede editar; (None, redirect) si ya fue confirmado."""
    rel = get_object_or_404(Relevamiento, pk=pk, tipo_registro=tipo)
    bloqueo = bloquear_si_completo(request, rel)
    return (None, bloqueo) if bloqueo else (rel, None)

def conflicto_editable(request, pk):
    rel = get_object_or_404(Relevamiento, pk=pk, tipo_registro='conflicto')

    # Ownership
    if rel.encuestador_id != request.user.id and not request.user.is_superuser:
        messages.error(request, 'No tenés permiso para editar este relevamiento.')
        return (None, redirect('relevamiento:encuestador_dashboard'))

    bloqueo = bloquear_si_completo(request, rel)
    return (None, bloqueo) if bloqueo else (rel, None)

def conflicto_editar_lote(request, rel):
    """Edita los datos del lote de un conflicto ya creado (lápiz del resumen)."""
    orden = rel.orden_trabajo
    datos_geo = datos_geograficos_desde_orden(orden)
    colonia = datos_geo['colonia']

    if request.method == 'POST':
        form = RelevamientoConflictoParte1Form(
            request.POST,
            instance=rel,
            colonia=colonia,
        )
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                messages.success(request, 'Datos del lote actualizados.')
                if rel.estado_carga == 'parte_4':
                    return redirect('relevamiento:continuar_encuesta', pk=rel.pk, parte='encuesta')
                return redirect('relevamiento:continuar_conflicto', pk=rel.pk, parte='pretendientes')
            except IntegrityError:
                form.add_error(
                    'manzana',
                    "Ya existe otro relevamiento con esa manzana y lote en esta colonia."
                )
                messages.error(request, 'Ese lote ya está registrado en esta colonia.')
            except Exception:
                logger.exception("Error editando lote del conflicto %s", rel.pk)
                messages.error(request, 'Ocurrió un error inesperado. Contacte al administrador.')
        else:
            messages.error(request, 'Hay errores en el formulario. Revise los campos marcados.')
    else:
        form = RelevamientoConflictoParte1Form(
            instance=rel,
            colonia=colonia,
        )

    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/conflicto/cuestionario_conflicto_datos_lote.html',
        {
            'form': form,
            'orden': orden,
            'datos_geo': datos_geo,
            'editando': True,
            'title': f'Encuesta #{rel.pk} (Conflicto) — Editar lote',
        },
    )

def bloquear_si_completo(request, relevamiento):
    """None si se puede editar; un redirect al resumen si ya fue confirmado."""
    if relevamiento.estado_carga == 'completo':
        messages.warning(request, 'Este relevamiento ya fue confirmado y no se puede editar.')
        return redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='encuesta')
    return None

def volver_al_resumen(rel):
    if rel.tipo_registro in MODOS_WIZARD:
        return redirect('relevamiento:continuar_encuesta', pk=rel.pk, parte='encuesta')
    return redirect('relevamiento:resumen_relevamiento', pk=rel.pk)

# ─────────────────────────────────────────────
# MODO SERVICIO
# ─────────────────────────────────────────────
@login_required
@encuestador_required
def cuestionario_servicio(request, orden_id):
    """SERVICIO – Parte Única: lote + instituciones + responsable + uso + mejoras + cierre."""
    orden = get_object_or_404(OrdenTrabajo, pk=orden_id)

    if not orden.formulario_habilitado:
        messages.warning(request, 'El formulario de relevamiento no está habilitado.')
        return redirect('relevamiento:encuestador_dashboard')

    datos_geo = datos_geograficos_desde_orden(orden)

    InstitucionFS = inlineformset_factory(
        Relevamiento, InstitucionEnLote, form=InstitucionEnLoteForm, 
        extra=1, can_delete=True, fk_name='relevamiento'
    )

    if request.method == 'POST':
        servicio_cuestionario = RelevamientoServicioParte1Form(request.POST)
        form_cierre = RelevamientoCierreForm(request.POST)

        if servicio_cuestionario.is_valid() and form_cierre.is_valid():
            try:
                with transaction.atomic():
                    rel = servicio_cuestionario.save(commit=False)
                    rel.colonia = datos_geo['colonia']
                    rel.distrito = datos_geo['distrito']
                    rel.departamento = datos_geo['departamento']
                    rel.orden_trabajo = orden
                    rel.encuestador = request.user
                    rel.tipo_registro = 'servicio'
                    rel.condicion_vivienda = 'servicio'
                    rel.vive_en_lote = False
                    rel.estado_carga = 'parte_4'
                    rel.save()
                    servicio_cuestionario.save_m2m()

                    # Guardamos el cierre (que incluye las mejoras)
                    form_cierre.instance = rel
                    form_cierre.save()

                    # Ahora validamos y guardamos instituciones (con el relevamiento guardado)
                    institucion_formset = InstitucionFS(request.POST, instance=rel)
                    if institucion_formset.is_valid():
                        institucion_formset.save()
                        messages.success(request, 'Datos y cierre guardados correctamente.')
                        return redirect('relevamiento:continuar_encuesta', pk=rel.pk, parte='encuesta')
                    else:
                        transaction.set_rollback(True)
                        avisar_errores(request, servicio_cuestionario, institucion_formset, form_cierre)
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            # Crear el formset sin validar para mostrar errores del form principal
            institucion_formset = InstitucionFS(request.POST)
            avisar_errores(request, servicio_cuestionario, institucion_formset, form_cierre)
    else:
        servicio_cuestionario = RelevamientoServicioParte1Form()
        form_cierre = RelevamientoCierreForm()
        institucion_formset = InstitucionFS()

    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/servicio/cuestionario_servicio_parte1.html',
        {
            'form': servicio_cuestionario,
            'servicio_cuestionario': servicio_cuestionario,
            'form_cierre': form_cierre,
            'institucion_formset': institucion_formset,
            'orden': orden,
            'datos_geo': datos_geo,
            'title': f'Nueva Encuesta (Servicio) — {orden}',
        },
    )

@login_required
@encuestador_required
def continuar_servicio(request, pk, parte):
    rel, bloqueo = relevamiento_editable(request, pk, 'servicio')
    if bloqueo:
        return bloqueo

    if parte == 'lote':
        return servicio_editar_lote(request, rel)

    messages.error(request, f'Parte "{parte}" no reconocida.')
    return redirect('relevamiento:encuestador_dashboard')

def servicio_editar_lote(request, rel):
    """Edita lote, responsable y uso del lote de un Servicio ya creado."""
    orden = rel.orden_trabajo
    datos_geo = datos_geograficos_desde_orden(orden)

    InstitucionFS = inlineformset_factory(
        Relevamiento, InstitucionEnLote, form=InstitucionEnLoteForm,
        extra=0, can_delete=True, fk_name='relevamiento'
    )

    if request.method == 'POST':
        form = RelevamientoServicioParte1Form(request.POST, instance=rel)
        form_cierre = RelevamientoCierreForm(request.POST, instance=rel)
        institucion_formset = InstitucionFS(request.POST, instance=rel)

        if form.is_valid() and form_cierre.is_valid() and institucion_formset.is_valid():
            form.save()
            form_cierre.save()
            institucion_formset.save()
            messages.success(request, 'Datos actualizados.')
            if rel.estado_carga == 'parte_4':
                return redirect('relevamiento:continuar_encuesta', pk=rel.pk, parte='encuesta')
            return redirect('relevamiento:continuar_servicio', pk=rel.pk, parte='cierre')
        avisar_errores(request, form, institucion_formset, form_cierre)
    else:
        form = RelevamientoServicioParte1Form(instance=rel)
        form_cierre = RelevamientoCierreForm(instance=rel)
        institucion_formset = InstitucionFS(instance=rel)

    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/servicio/cuestionario_servicio_parte1.html',
        {
            'form': form,
            'servicio_cuestionario': form,
            'form_cierre': form_cierre,
            'institucion_formset': institucion_formset,
            'orden': orden,
            'datos_geo': datos_geo,
            'editando': True,
            'title': f'Encuesta #{rel.pk} (Servicio) — Editar lote',
        },
    )

@login_required
@encuestador_required
def mis_encuestas(request):
    """Vista para gestionar y filtrar encuestas/relevamientos del encuestador."""
   
    # Filtrado opcional por query param 'colonia'
    colonia_q = request.GET.get('colonia')

    # Base queryset: relevamientos del usuario actual
    relevamientos_qs = Relevamiento.objects.filter(encuestador=request.user)

    if colonia_q:
        # Intentar interpretar como ID; si falla, filtrar por nombre (icontains)
        try:
            colonia_id = int(colonia_q)
            relevamientos_qs = relevamientos_qs.filter(colonia__id=colonia_id)
        except (ValueError, TypeError):
            relevamientos_qs = relevamientos_qs.filter(colonia__nombre__icontains=colonia_q)

    relevamientos = relevamientos_qs.select_related(
        'colonia',
        'distrito',
        'departamento',
        'orden_trabajo'
    ).order_by('-creado_en')
    
    # Serializar relevamientos a JSON
    relevamientos_data = []
    for rel in relevamientos:
        relevamientos_data.append({
            'id': rel.id,
            'fechaRegistro': rel.creado_en.strftime('%Y-%m-%d'),
            'departamento': rel.departamento.nombre if rel.departamento else '',
            'distrito': rel.distrito.nombre if rel.distrito else '',
            'colonia': rel.colonia.nombre if rel.colonia else '',
            'colonia_id': rel.colonia.id if rel.colonia else '',
            'manzana': rel.manzana or 'Sin datos',
            'loteIndert': rel.lote_indert or 'Sin datos',
            'loteSirt': rel.lote_sirt or 'Sin datos',
            'condicionVivienda': rel.get_condicion_vivienda_display() if rel.condicion_vivienda else 'Sin datos',
            'condicionEncuestado': rel.get_condicion_encuestado_display() if rel.condicion_encuestado else 'Sin datos',
            'quien_es_el_ocupante': rel.quien_es_el_ocupante or 'Sin información',
            'cedula_ocupante': rel.cedula_ocupante or 'Sin información',
            'sexo_ocupante': rel.get_sexo_ocupante_display() if rel.sexo_ocupante else 'Sin información',   
            'observaciones': rel.observacion_encuesta or 'Sin observaciones',
            'formularioHabilitado': rel.orden_trabajo.formulario_habilitado if rel.orden_trabajo else False,
            'firmo_solicitud': bool(rel.firmo_solicitud),
            'firmoSolicitud': bool(rel.firmo_solicitud),
        })
    
    context = {
        'relevamientos': relevamientos,
        'relevamientos_json': json.dumps(relevamientos_data, ensure_ascii=False),
    }
    return render(request, 'includes/relevamiento/encuestador/mis_encuestas.html', context)

@login_required
def agregar_fotos(request, pk):
    """Sube fotos a un relevamiento, agrupadas en las 4 categorías del formulario."""
    rel = get_object_or_404(Relevamiento, pk=pk)

    if request.method == 'POST':
        form = FotosRelevamientoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    total = form.guardar(rel, request.user)
                if total:
                    messages.success(request, f'Se subieron {total} foto(s).')
                else:
                    messages.warning(request, 'No se seleccionó ninguna foto.')
                return volver_al_resumen(rel)
            except Exception as e:
                messages.error(request, f'Error al subir fotos: {str(e)}')
    else:
        form = FotosRelevamientoForm()

    return render(request, 'relevamiento/agregar_fotos.html', {
        'form': form,
        'relevamiento': rel,
    })

@login_required
@encuestador_required
def editar_encuesta_relevamiento(request, pk):
    """Dispatcher: manda al wizard correcto según tipo_registro."""
    rel = get_object_or_404(Relevamiento, pk=pk)

    if not rel.orden_trabajo:
        messages.error(request, 'Este relevamiento no tiene orden de trabajo asociada.')
        return redirect('relevamiento:encuestador_dashboard')

    es_encuestador = rel.encuestador == request.user
    esta_en_equipo = rel.orden_trabajo.equipos_asignados.filter(encuestadores=request.user).exists()
    if not (es_encuestador or esta_en_equipo or request.user.is_superuser):
        messages.error(request, 'No tiene permisos para editar este relevamiento.')
        return redirect('relevamiento:encuestador_dashboard')

    if rel.estado_carga == 'completo':
        return redirect('relevamiento:continuar_encuesta', pk=pk, parte='encuesta')

    if rel.tipo_registro == 'ocupante':
        return redirect('relevamiento:continuar_encuesta', pk=pk, parte='identificacion')
    if rel.tipo_registro == 'conflicto':
        return redirect('relevamiento:continuar_conflicto', pk=pk, parte='lote')
    if rel.tipo_registro == 'servicio':
        return redirect('relevamiento:continuar_servicio', pk=pk, parte='lote')

    messages.error(request, f'Tipo de relevamiento "{rel.tipo_registro}" no soportado.')
    return redirect('relevamiento:encuestador_dashboard')

