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
    InstitucionEnLote, FotoRelevamiento,
    ArchivoSubcoordinador,
)
from .forms import (
    RelevamientoForm, RelevamientoParte1Form, RelevamientoParte2Form,
    RelevamientoMejorasForm,
    PretendienteForm, ViviendaForm, MiembroForm,
    CultivoForm, ProduccionGanaderaForm, InstitucionEnLoteForm,
    DocumentoForm, FotosRelevamientoForm,
    ViviendaPretendienteFormSet,
)
from django.db import transaction
from gerencia.models import SolicitudRelevamientoAudit, SolicitudRelevamiento
from administrador.models import Grupo
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden, request
from django.views.decorators.http import require_POST
import os
import re
import json

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
        datos_geo = _datos_geograficos_desde_orden(orden)
        
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
    datos_geo = _datos_geograficos_desde_orden(orden)
    
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


# ─────────────────────────────────────────────
# DASHBOARD ENCUESTADOR
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# MAPEO DE MODO -> TEMPLATE DEL FORMULARIO
# ─────────────────────────────────────────────

TEMPLATE_MAP = {
    'ocupante': 'includes/relevamiento/encuestador/formulario_relevamiento/formulario_ocupante.html',
    'conflicto': 'includes/relevamiento/encuestador/formulario_relevamiento/formulario_conflicto.html',
    'servicio': 'includes/relevamiento/encuestador/formulario_relevamiento/formulario_servicio.html',
    'fraccionamiento': 'includes/relevamiento/encuestador/formulario_relevamiento/formulario_fraccionamiento.html',
}


def _detectar_modo_relevamiento(rel):
    """Infiere el modo/tipo de registro de un Relevamiento existente."""
    if rel.pretendientes.exists():
        return 'conflicto'
    uso_lote_servicio = rel.uso_lote_servicio or []
    if 'institucion_organizacion' in uso_lote_servicio or rel.condicion_vivienda == 'servicio':
        return 'servicio'
    if rel.parent_lote_id is not None:
        return 'fraccionamiento'
    return 'ocupante'



# ─────────────────────────────────────────────
# UTILIDAD INTERNA: extraer datos geográficos
# de una OrdenTrabajo
# ─────────────────────────────────────────────

def _datos_geograficos_desde_orden(orden):
    """
    Dado un OrdenTrabajo, devuelve un dict con {colonia, distrito, departamento}
    extraídos de la solicitud asociada, o None para cada uno si no existen.
    """
    solicitud = orden.solicitud
    colonia = solicitud.colonia if solicitud else None

    distrito = None
    departamento = None
    if colonia:
        # Colonia tiene M2M a distritos; tomamos el primero disponible
        primer_distrito = colonia.distritos.select_related('departamento').first()
        if primer_distrito:
            distrito = primer_distrito
            departamento = primer_distrito.departamento

    return {
        'colonia': colonia,
        'distrito': distrito,
        'departamento': departamento,
    }


def _procesar_viviendas_pretendiente(request, pretendiente, index, MiembroFS):
    """Guarda las viviendas y miembros anidados de un pretendiente (modo conflicto).

    Usa los prefijos dinámicos 'viviendas_pret_{index}' y 'miembros_pret_{index}_viv_{j}',
    en espejo del manejo de viviendas del ocupante principal.
    """
    viv_prefix = f'viviendas_pret_{index}'
    if f'{viv_prefix}-TOTAL_FORMS' not in request.POST:
        return
    viv_fs = ViviendaPretendienteFormSet(request.POST, request.FILES, instance=pretendiente, prefix=viv_prefix)
    if not viv_fs.is_valid():
        return
    for j, viv_form in enumerate(viv_fs):
        if not viv_form.cleaned_data or viv_form.cleaned_data.get('DELETE', False):
            continue
        vivienda = viv_form.save(commit=False)
        vivienda.pretendiente = pretendiente
        if j == 0 and not vivienda.es_principal:
            vivienda.es_principal = True
        vivienda.save()
        viv_form.save_m2m()

        miem_prefix = f'miembros_pret_{index}_viv_{j}'
        if f'{miem_prefix}-TOTAL_FORMS' in request.POST:
            miem_fs = MiembroFS(request.POST, request.FILES, instance=vivienda, prefix=miem_prefix)
            if miem_fs.is_valid():
                miem_fs.save()


def _construir_formsets_pretendiente(request, pretendiente_formset, MiembroFS):
    """Construye, para renderizado en el template, los formsets anidados de
    vivienda y miembros de cada pretendiente (modo conflicto).

    Devuelve dos dicts indexados por la posición del pretendiente en el formset:
    {i: ViviendaPretendienteFormSet} y {i: {j: MiembroFormSet}}.
    """
    pretendiente_vivienda_formsets = {}
    pretendiente_miembro_formsets = {}
    for i, pret_form in enumerate(pretendiente_formset.forms):
        instance = pret_form.instance if pret_form.instance.pk else Pretendiente()
        viv_prefix = f'viviendas_pret_{i}'
        if request.method == 'POST' and f'{viv_prefix}-TOTAL_FORMS' in request.POST:
            viv_fs = ViviendaPretendienteFormSet(request.POST, request.FILES, instance=instance, prefix=viv_prefix)
        else:
            viv_fs = ViviendaPretendienteFormSet(instance=instance, prefix=viv_prefix)
        pretendiente_vivienda_formsets[i] = viv_fs

        miembro_fs_por_viv = {}
        for j, viv_form in enumerate(viv_fs.forms):
            miem_prefix = f'miembros_pret_{i}_viv_{j}'
            if request.method == 'POST' and f'{miem_prefix}-TOTAL_FORMS' in request.POST:
                miembro_fs_por_viv[j] = MiembroFS(request.POST, request.FILES, prefix=miem_prefix)
            elif viv_form.instance.pk:
                miembro_fs_por_viv[j] = MiembroFS(instance=viv_form.instance, prefix=miem_prefix)
            else:
                miembro_fs_por_viv[j] = MiembroFS(prefix=miem_prefix)
        pretendiente_miembro_formsets[i] = miembro_fs_por_viv

    return pretendiente_vivienda_formsets, pretendiente_miembro_formsets


# ─────────────────────────────────────────────
# FORMULARIO DESDE UNA ORDEN (crear) - OBLIGATORIO
# ─────────────────────────────────────────────

@login_required
@encuestador_required
def formulario_desde_orden(request, orden_id):
    """
    Crea un nuevo Relevamiento vinculado a una OrdenTrabajo.
    Los campos departamento, distrito y colonia se pre-cargan desde
    la solicitud de la orden y se bloquean en el formulario.

    IMPORTANTE: Esta es la ÚNICA forma de crear relevamientos.
    No se permite crear relevamientos sin orden de trabajo asociada.
    """
    orden = get_object_or_404(OrdenTrabajo, pk=orden_id)

    if not orden.formulario_habilitado:
        messages.warning(
            request,
            'El formulario de relevamiento no está habilitado. '
            'Contacte al coordinador de campo para habilitarlo.'
        )
        return redirect('relevamiento:encuestador_dashboard')

    modo = request.POST.get('tipo_registro') or request.GET.get('modo', 'ocupante')
    if modo not in TEMPLATE_MAP:
        modo = 'ocupante'

    # El modo Ocupante ahora es un wizard de 4 partes con guardado real en
    # cada paso — vive en su propia vista. Conflicto/Servicio/Fraccionamiento
    # siguen con el formulario único de siempre, sin cambios.
    if modo == 'ocupante' and request.method == 'GET':
        return redirect('relevamiento:ocupante_parte1', orden_id=orden_id)


    datos_geo = _datos_geograficos_desde_orden(orden)
    initial = {
        'colonia': datos_geo['colonia'],
        'distrito': datos_geo['distrito'],
        'departamento': datos_geo['departamento'],
        'tipo_registro': modo,
    }
    

    ViviendaFS = inlineformset_factory(
        Relevamiento, Vivienda, form=ViviendaForm, extra=0, can_delete=True, fk_name='relevamiento'
    )
    MiembroFS = inlineformset_factory(
        Vivienda, Miembro, form=MiembroForm, extra=0, can_delete=True, fk_name='vivienda'
    )
    CultivoFS = inlineformset_factory(
        Relevamiento, Cultivo, form=CultivoForm, extra=0, can_delete=True, fk_name='relevamiento'
    )
    GanaderiaFS = inlineformset_factory(
        Relevamiento, ProduccionGanadera, form=ProduccionGanaderaForm, extra=0, can_delete=True, fk_name='relevamiento'
    )
    InstitucionFS = inlineformset_factory(
        Relevamiento, InstitucionEnLote, form=InstitucionEnLoteForm, extra=0, can_delete=True, fk_name='relevamiento'
    )
    PretendienteFS = inlineformset_factory(
        Relevamiento, Pretendiente, form=PretendienteForm, extra=0, can_delete=True
    )
    DocumentoFS = inlineformset_factory(
        Relevamiento, Documento, form=DocumentoForm, extra=0, can_delete=True
    )
    PrincipalesFS = inlineformset_factory(
        Relevamiento, Miembro, form=MiembroForm, extra=0, can_delete=True, fk_name='relevamiento'
    )

    if request.method == 'POST':
        form = RelevamientoForm(request.POST, request.FILES, initial=initial, modo=modo)
        vivienda_formset = ViviendaFS(request.POST, request.FILES, prefix='viviendas')
        cultivo_formset = CultivoFS(request.POST, request.FILES, prefix='cultivos')
        ganaderia_formset = GanaderiaFS(request.POST, request.FILES, prefix='ganaderia')
        institucion_formset = InstitucionFS(request.POST, request.FILES, prefix='instituciones')
        pretendiente_formset = PretendienteFS(request.POST, request.FILES, prefix='pretendientes')
        documento_formset = DocumentoFS(request.POST, request.FILES, prefix='documentos')
        principales_formset = PrincipalesFS(request.POST, request.FILES, prefix='principales')

    
        vivienda_presente = 'viviendas-TOTAL_FORMS' in request.POST
        cultivo_presente = 'cultivos-TOTAL_FORMS' in request.POST
        ganaderia_presente = 'ganaderia-TOTAL_FORMS' in request.POST
        institucion_presente = 'instituciones-TOTAL_FORMS' in request.POST
        pretendiente_presente = 'pretendientes-TOTAL_FORMS' in request.POST
        documento_presente = 'documentos-TOTAL_FORMS' in request.POST
        principales_presente = 'principales-TOTAL_FORMS' in request.POST

        all_valid = (
            form.is_valid()
            and (not vivienda_presente or vivienda_formset.is_valid())
            and (not cultivo_presente or cultivo_formset.is_valid())
            and (not ganaderia_presente or ganaderia_formset.is_valid())
            and (not institucion_presente or institucion_formset.is_valid())
            and (not pretendiente_presente or pretendiente_formset.is_valid())
            and (not documento_presente or documento_formset.is_valid())
            and (not principales_presente or principales_formset.is_valid())
        )

        if all_valid:
            try:
                with transaction.atomic():
                    relevamiento = form.save(commit=False)
                    relevamiento.colonia = datos_geo['colonia']
                    relevamiento.distrito = datos_geo['distrito']
                    relevamiento.departamento = datos_geo['departamento']
                    relevamiento.orden_trabajo = orden
                    relevamiento.encuestador = request.user
                    relevamiento.save()
                    form.save_m2m()

                    for pret_form in pretendiente_formset:
                        if pret_form.cleaned_data and not pret_form.cleaned_data.get('DELETE', False):
                            pretendiente = pret_form.save(commit=False)
                            pretendiente.relevamiento = relevamiento
                            pretendiente.save()
                            pret_form.save_m2m()
                            _procesar_viviendas_pretendiente(request, pretendiente, pretendiente_formset.forms.index(pret_form), MiembroFS)

                # ── Guardado de viviendas ─────────────────────────────────────────────
                # 1ra pasada: guardamos (sin commit) y numeramos secuencialmente SOLO
                # las que sobreviven (no están marcadas DELETE). "i" se conserva como
                # el índice original del formset, porque los miembros anidados usan
                # el prefijo "miembros_viv_{i}" armado por el JS con ese mismo índice.
                viviendas_guardadas = []  # [(i, vivienda, viv_form), ...]
                numero_actual = 1

                for i, viv_form in enumerate(vivienda_formset):
                    if viv_form.cleaned_data and not viv_form.cleaned_data.get('DELETE', False):
                        vivienda = viv_form.save(commit=False)
                        vivienda.relevamiento = relevamiento
                        vivienda.numero = numero_actual
                        numero_actual += 1
                        viviendas_guardadas.append((i, vivienda, viv_form))

                # 2da pasada: garantizamos que haya EXACTAMENTE una vivienda principal.
                principales = [v for _, v, _ in viviendas_guardadas if v.es_principal]
                if not principales and viviendas_guardadas:
                    # Nadie quedó marcado: la primera pasa a ser la principal por defecto.
                    viviendas_guardadas[0][1].es_principal = True
                elif len(principales) > 1:
                    # Por algún motivo hay varias marcadas (no debería pasar gracias al
                    # JS, pero nos cubrimos): nos quedamos solo con la primera.
                    for vivienda in principales[1:]:
                        vivienda.es_principal = False

                # 3ra pasada: guardado definitivo + miembros anidados de cada vivienda.
                for i, vivienda, viv_form in viviendas_guardadas:
                    vivienda.save()
                    viv_form.save_m2m()

                    miem_prefix = f'miembros_viv_{i}'
                    if f'{miem_prefix}-TOTAL_FORMS' in request.POST:
                        miem_fs = MiembroFS(
                            request.POST, request.FILES,
                            instance=vivienda,
                            prefix=miem_prefix,
                        )
                        if miem_fs.is_valid():
                            miem_fs.save()

                for cultivo_form in cultivo_formset:
                    if cultivo_form.cleaned_data and not cultivo_form.cleaned_data.get('DELETE', False):
                        cultivo = cultivo_form.save(commit=False)
                        cultivo.relevamiento = relevamiento
                        cultivo.save()

                for ganaderia_form in ganaderia_formset:
                    if ganaderia_form.cleaned_data and not ganaderia_form.cleaned_data.get('DELETE', False):
                        ganaderia = ganaderia_form.save(commit=False)
                        ganaderia.relevamiento = relevamiento
                        ganaderia.save()

                for inst_form in institucion_formset:
                    if inst_form.cleaned_data and not inst_form.cleaned_data.get('DELETE', False):
                        inst = inst_form.save(commit=False)
                        inst.relevamiento = relevamiento
                        inst.save()

                for doc_form in documento_formset:
                    if doc_form.cleaned_data and not doc_form.cleaned_data.get('DELETE', False):
                        doc = doc_form.save(commit=False)
                        doc.relevamiento = relevamiento
                        doc.save()

                # ── Ocupante / Cónyuge ────────────────────────────────────────────────
                # Van siempre colgados de relevamiento_id. Si además hay vivienda
                # principal, se linkean también a esa vivienda (sin duplicar el registro)
                # para que aparezcan solos en su tabla de Población.
                vivienda_principal = viviendas_guardadas[0][1] if viviendas_guardadas else None
                for p_form in principales_formset:
                    if p_form.cleaned_data and not p_form.cleaned_data.get('DELETE', False):
                        persona = p_form.save(commit=False)
                        persona.relevamiento = relevamiento
                        if vivienda_principal and persona.parentesco in ('Ocupante', 'Cónyuge'):
                            persona.vivienda = vivienda_principal
                        persona.save()

                messages.success(request, 'Registro creado correctamente.')
                return redirect('relevamiento:resumen_relevamiento', pk=relevamiento.pk)
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            messages.error(request, 'Hay errores en el formulario. Revise los campos marcados.')
    else:
        form = RelevamientoForm(initial=initial, modo=modo)
        vivienda_formset = ViviendaFS(prefix='viviendas')
        cultivo_formset = CultivoFS(prefix='cultivos')
        ganaderia_formset = GanaderiaFS(prefix='ganaderia')
        institucion_formset = InstitucionFS(prefix='instituciones')
        pretendiente_formset = PretendienteFS(prefix='pretendientes')
        documento_formset = DocumentoFS(prefix='documentos')
        principales_formset = PrincipalesFS(prefix='principales')

    # Formsets de miembros por vivienda (prefijo dinámico miembros_viv_N)
    vivienda_miembro_formsets = {}
    pret_vivienda_template_formset = ViviendaPretendienteFormSet(prefix='viviendas_pret_0')
    miembro_template_formset = MiembroFS(prefix='miembros_viv_0')
    for i in range(vivienda_formset.total_form_count()):
        miem_prefix = f'miembros_viv_{i}'
        if request.method == 'POST' and f'{miem_prefix}-TOTAL_FORMS' in request.POST:
            vivienda_miembro_formsets[i] = MiembroFS(
                request.POST, request.FILES, prefix=miem_prefix
            )
        else:
            vivienda_miembro_formsets[i] = MiembroFS(prefix=miem_prefix)

    pretendiente_vivienda_formsets, pretendiente_miembro_formsets = _construir_formsets_pretendiente(
        request, pretendiente_formset, MiembroFS
    )
    

    context = {
        'form': form,
        'vivienda_formset': vivienda_formset,
        'vivienda_miembro_formsets': vivienda_miembro_formsets,
        'miembro_template_formset': miembro_template_formset,
        'pret_vivienda_template_formset': pret_vivienda_template_formset,
        'principales_formset': principales_formset,
        'cultivo_formset': cultivo_formset,
        'ganaderia_formset': ganaderia_formset,
        'institucion_formset': institucion_formset,
        'pretendiente_formset': pretendiente_formset,
        'pretendiente_vivienda_formsets': pretendiente_vivienda_formsets,
        'pretendiente_miembro_formsets': pretendiente_miembro_formsets,
        'documento_formset': documento_formset,
        'orden': orden,
        'datos_geo': datos_geo,
        'title': f'Nueva Encuesta — {orden}',
    }
    return render(request, TEMPLATE_MAP[modo], context)

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

    datos_geo = _datos_geograficos_desde_orden(orden)
    initial = {
        'colonia': datos_geo['colonia'],
        'distrito': datos_geo['distrito'],
        'departamento': datos_geo['departamento'],
    }


    if request.method == 'POST':
        form = RelevamientoParte1Form(request.POST, initial=initial)

        if form.is_valid():
            try:
                with transaction.atomic():
                    relevamiento = form.save(commit=False)
                    relevamiento.colonia = datos_geo['colonia']
                    relevamiento.distrito = datos_geo['distrito']
                    relevamiento.departamento = datos_geo['departamento']
                    relevamiento.orden_trabajo = orden
                    relevamiento.encuestador = request.user
                    relevamiento.tipo_registro = 'ocupante'
                    relevamiento.estado_carga = 'parte_1'
                    relevamiento.save()
                    form.save_m2m()

                messages.success(request, 'Parte 1 guardada. Continuá con los datos del lote.')
                return redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='lote')
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            messages.error(request, 'Hay errores en el formulario. Revise los campos marcados.')
    else:
        form = RelevamientoParte1Form(initial=initial)

    context = {
        'form': form,
        'orden': orden,
        'datos_geo': datos_geo,
        'title': f'Nueva Encuesta (Parte 1 de 4) — {orden}',
    }
    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/cuestionario_ocupante_parte1.html',
        context,
    )

@login_required
@encuestador_required
def continuar_encuesta(request, pk, parte):
    relevamiento = get_object_or_404(Relevamiento, pk=pk)

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

    if request.method == 'POST':
        form = RelevamientoParte2Form(request.POST, instance=relevamiento)
        if form.is_valid():
            rel = form.save(commit=False)
            rel.condicion_encuestado = 'ocupante'  # fijo: este wizard es siempre Ocupante
            rel.estado_carga = 'parte_2'
            rel.save()
            form.save_m2m()

            messages.success(request, 'Parte 2 guardada.')

            # Acá se define la ruta del wizard.
            if rel.condicion_vivienda == 'sin_vivienda':
                return destino_tras_guardar(
                    request, relevamiento,
                    redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='productivos')
                )
            return destino_tras_guardar(
                request, relevamiento,
                redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='vivienda')
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
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/cuestionario_ocupante_parte2.html',
        context,
    )

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
                        if miem_fs.is_valid():
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
            messages.error(request, 'Hay errores en el formulario. Revise los campos marcados.')
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
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/cuestionario_ocupante_parte3_vivienda.html',
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
        form = RelevamientoMejorasForm(request.POST, instance=relevamiento)
        cultivo_formset = CultivoFS(request.POST, instance=relevamiento, prefix='cultivos')
        ganaderia_formset = GanaderiaFS(request.POST, instance=relevamiento, prefix='ganaderia')

        if form.is_valid() and cultivo_formset.is_valid() and ganaderia_formset.is_valid():
            try:
                with transaction.atomic():
                    rel = form.save(commit=False)
                    rel.estado_carga = 'parte_3'
                    rel.save()
                    form.save_m2m()
                    cultivo_formset.save()
                    ganaderia_formset.save()

                messages.success(request, 'Datos productivos y mejoras guardados.')
                return destino_tras_guardar(
                    request, relevamiento,
                    redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='encuesta')
                )
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            messages.error(request, 'Hay errores en el formulario. Revise los campos marcados.')
    else:
        form = RelevamientoMejorasForm(instance=relevamiento)
        cultivo_formset = CultivoFS(instance=relevamiento, prefix='cultivos')
        ganaderia_formset = GanaderiaFS(instance=relevamiento, prefix='ganaderia')

    context = {
        'relevamiento': relevamiento,
        'form': form,
        'cultivo_formset': cultivo_formset,
        'ganaderia_formset': ganaderia_formset,
        'title': f'Encuesta #{relevamiento.pk} — Parte 3 de 4',
        'origen_resumen': request.GET.get('origen') == 'resumen',
    }
    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/cuestionario_ocupante_parte3_productivos.html',
        context,
    )

def continuar_parte1_editar(request, relevamiento):
    """Edición de los datos de la Parte 1 (identificación/ocupante) para
    un Relevamiento YA creado. Se usa desde el lápiz 'Editar' del resumen."""
    orden = relevamiento.orden_trabajo
    datos_geo = _datos_geograficos_desde_orden(orden)

    if request.method == 'POST':
        form = RelevamientoParte1Form(request.POST, instance=relevamiento)
        if form.is_valid():
            rel = form.save(commit=False)
            rel.colonia = datos_geo['colonia']
            rel.distrito = datos_geo['distrito']
            rel.departamento = datos_geo['departamento']
            rel.save()
            form.save_m2m()
            messages.success(request, 'Datos actualizados.')
            return destino_tras_guardar(
                request, relevamiento,
                redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='lote')
            )
        else:
            messages.error(request, 'Hay errores en el formulario. Revise los campos marcados.')
    else:
        form = RelevamientoParte1Form(instance=relevamiento)

    context = {
        'form': form,
        'orden': orden,
        'datos_geo': datos_geo,
        'origen_resumen': request.GET.get('origen') == 'resumen',
        'title': f'Encuesta #{relevamiento.pk} — Editar identificación',
    }
    return render(
        request,
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/cuestionario_ocupante_parte1.html',
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

def _meta_seccion(titulo):
    """Devuelve (icono_fa, tono) para una sección según su título."""
    t = titulo.lower()
    if t.startswith('lote'):                    return ('fa-map-marker-alt', 'blue')
    if t.startswith('ocupante'):                return ('fa-user', 'teal')
    if t.startswith('cónyuge'):                 return ('fa-heart', 'rose')
    if t.startswith('condición'):               return ('fa-house-circle-check', 'amber')
    if t.startswith('vivienda'):                return ('fa-house-chimney', 'green')
    if t.startswith('instituciones'):           return ('fa-building-columns', 'purple')
    if t.startswith('producción'):              return ('fa-seedling', 'orange')
    return ('fa-circle-dot', 'slate')

secciones = []

def agregar(titulo, editar, items):
    if items:
        icon, tone = _meta_seccion(titulo)
        secciones.append({
            'titulo': titulo,
            'editar': editar,
            'items':  items,
            'icon':   icon,
            'tone':   tone,
        })

def continuar_parte4_resumen(request, relevamiento):
    """PARTE 4: resumen final. Antes de confirmar muestra el botón de cierre;
    después de confirmar es la pantalla definitiva (Nueva encuesta / Fotos)."""
    from .models import USO_LOTE_OCUPANTE_CHOICES, MEJORAS_CHOICES, EQUIPAMIENTOS_CHOICES

    r = relevamiento
    orden = r.orden_trabajo

    if request.method == 'POST' and r.estado_carga != 'completo':
        r.estado_carga = 'completo'
        r.fecha_de_encuesta = timezone.now()
        r.save(update_fields=['estado_carga', 'fecha_de_encuesta'])
        messages.success(request, f'Relevamiento #{r.pk} confirmado y finalizado correctamente.')
        return redirect('relevamiento:continuar_encuesta', pk=r.pk, parte='encuesta')

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
            icon, tone = _meta_seccion(titulo)
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
        ('Encargado', r.encargado_residencia), ('Parentesco', r.parentesco),
        ('Uso del lote', _etiquetas(r.uso_lote_ocupante, USO_LOTE_OCUPANTE_CHOICES)),
    ))

    for v in r.viviendas.all().order_by('numero'):
        poblacion = '; '.join(
            f'{m.nombre_miembro} ({m.relacion_con_lote})' if m.relacion_con_lote else m.nombre_miembro
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

    agregar('Instituciones / servicios', 'vivienda', _items(
        ('Registradas', ', '.join(i.nombre_servicio for i in r.instituciones.all())),
    ))
    agregar('Producción e infraestructura', 'productivos', _items(
        ('Cultivos', '; '.join(f'{c.get_tipo_cultivo_display()} · {c.hectareas} ha' for c in r.cultivos.all())),
        ('Ganadería', '; '.join(f'{g.get_tipo_ganaderia_display()} × {g.cantidad}' for g in r.producciones_ganaderas.all())),
        ('Mejoras', _etiquetas(r.mejoras, MEJORAS_CHOICES)),
    ))

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
        'includes/relevamiento/encuestador/formulario_relevamiento/cuestionarios/cuestionario_ocupante_parte4_resumen.html',
        context,
    )

def destino_tras_guardar(request, relevamiento, destino_normal):
    """Si esta parte se abrió desde el resumen final (vía el lápiz de
    'Editar', que agrega ?origen=resumen) y el usuario la completa, lo
    mandamos de vuelta al resumen en vez de seguir avanzando por el wizard.
    Si no, sigue el flujo normal (Parte 1 → 2 → 3 → 4)."""
    origen = request.POST.get('origen') or request.GET.get('origen')
    if origen == 'resumen':
        return redirect('relevamiento:continuar_encuesta', pk=relevamiento.pk, parte='encuesta')
    return destino_normal

# ─────────────────────────────────────────────
# EDITAR RELEVAMIENTO (siempre con orden asociada)
# ─────────────────────────────────────────────

@login_required
@encuestador_required
def editar_encuesta_relevamiento(request, pk):
    """
    Edita un Relevamiento existente.
    Los campos geográficos permanecen bloqueados con los datos de su orden asociada.
    Solo el encuestador asignado a la orden puede editar el relevamiento.
    """
    rel = get_object_or_404(Relevamiento, pk=pk)

    if not rel.orden_trabajo:
        messages.error(request, 'Este relevamiento no tiene orden de trabajo asociada.')
        return redirect('relevamiento:encuestador_dashboard')

    orden = rel.orden_trabajo
    datos_geo = _datos_geograficos_desde_orden(orden)

    es_encuestador_asignado = rel.encuestador == request.user
    esta_en_equipo = orden.equipos_asignados.filter(encuestadores=request.user).exists()
    if not (es_encuestador_asignado or esta_en_equipo or request.user.is_superuser):
        messages.error(request, 'No tiene permisos para editar este relevamiento.')
        return redirect('relevamiento:encuestador_dashboard')

    ViviendaFS = inlineformset_factory(
        Relevamiento, Vivienda, form=ViviendaForm, extra=0, can_delete=True, fk_name='relevamiento'
    )
    MiembroFS = inlineformset_factory(
        Vivienda, Miembro, form=MiembroForm, extra=0, can_delete=True, fk_name='vivienda'
    )
    CultivoFS = inlineformset_factory(
        Relevamiento, Cultivo, form=CultivoForm, extra=0, can_delete=True, fk_name='relevamiento'
    )
    GanaderiaFS = inlineformset_factory(
        Relevamiento, ProduccionGanadera, form=ProduccionGanaderaForm, extra=0, can_delete=True, fk_name='relevamiento'
    )
    InstitucionFS = inlineformset_factory(
        Relevamiento, InstitucionEnLote, form=InstitucionEnLoteForm, extra=0, can_delete=True, fk_name='relevamiento'
    )
    PretendienteFS = inlineformset_factory(
        Relevamiento, Pretendiente, form=PretendienteForm, extra=0, can_delete=True
    )
    DocumentoFS = inlineformset_factory(
        Relevamiento, Documento, form=DocumentoForm, extra=0, can_delete=True
    )

    if request.method == 'POST':
        form = RelevamientoForm(request.POST, request.FILES, instance=rel)
        vivienda_formset = ViviendaFS(request.POST, request.FILES, instance=rel, prefix='viviendas')
        cultivo_formset = CultivoFS(request.POST, request.FILES, instance=rel, prefix='cultivos')
        ganaderia_formset = GanaderiaFS(request.POST, request.FILES, instance=rel, prefix='ganaderia')
        institucion_formset = InstitucionFS(request.POST, request.FILES, instance=rel, prefix='instituciones')
        pretendiente_formset = PretendienteFS(request.POST, request.FILES, instance=rel, prefix='pretendientes')
        documento_formset = DocumentoFS(request.POST, request.FILES, instance=rel, prefix='documentos')

        vivienda_presente = 'viviendas-TOTAL_FORMS' in request.POST
        cultivo_presente = 'cultivos-TOTAL_FORMS' in request.POST
        ganaderia_presente = 'ganaderia-TOTAL_FORMS' in request.POST
        institucion_presente = 'instituciones-TOTAL_FORMS' in request.POST
        pretendiente_presente = 'pretendientes-TOTAL_FORMS' in request.POST
        documento_presente = 'documentos-TOTAL_FORMS' in request.POST

        all_valid = (
            form.is_valid()
            and (not vivienda_presente or vivienda_formset.is_valid())
            and (not cultivo_presente or cultivo_formset.is_valid())
            and (not ganaderia_presente or ganaderia_formset.is_valid())
            and (not institucion_presente or institucion_formset.is_valid())
            and (not pretendiente_presente or pretendiente_formset.is_valid())
            and (not documento_presente or documento_formset.is_valid())
        )

        if all_valid:
            try:
                with transaction.atomic():
                    relevamiento = form.save(commit=False)
                    relevamiento.colonia = datos_geo['colonia']
                    relevamiento.distrito = datos_geo['distrito']
                    relevamiento.departamento = datos_geo['departamento']
                    relevamiento.orden_trabajo = orden
                    relevamiento.save()
                    form.save_m2m()

                    pretendiente_formset.save()
                    vivienda_formset.save()

                    for i, pret_form in enumerate(pretendiente_formset.forms):
                        if not pret_form.cleaned_data or pret_form.cleaned_data.get('DELETE', False):
                            continue
                        if pret_form.instance.pk:
                            _procesar_viviendas_pretendiente(request, pret_form.instance, i, MiembroFS)

                    # Miembros anidados por vivienda con prefijo dinámico
                    for i, viv_form in enumerate(vivienda_formset):
                        if not viv_form.cleaned_data or viv_form.cleaned_data.get('DELETE', False):
                            continue
                        vivienda = viv_form.instance
                        if not vivienda.pk:
                            continue
                        miem_prefix = f'miembros_viv_{i}'
                        if f'{miem_prefix}-TOTAL_FORMS' in request.POST:
                            miem_fs = MiembroFS(
                                request.POST, request.FILES,
                                instance=vivienda,
                                prefix=miem_prefix,
                            )
                            if miem_fs.is_valid():
                                miem_fs.save()

                    cultivo_formset.save()
                    ganaderia_formset.save()
                    institucion_formset.save()
                    documento_formset.save()

                messages.success(request, 'Relevamiento actualizado correctamente.')
                return redirect('relevamiento:resumen_relevamiento', pk=relevamiento.pk)
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            messages.error(request, 'Hay errores en el formulario.')
    else:
        form = RelevamientoForm(instance=rel)
        vivienda_formset = ViviendaFS(instance=rel, prefix='viviendas')
        cultivo_formset = CultivoFS(instance=rel, prefix='cultivos')
        ganaderia_formset = GanaderiaFS(instance=rel, prefix='ganaderia')
        institucion_formset = InstitucionFS(instance=rel, prefix='instituciones')
        pretendiente_formset = PretendienteFS(instance=rel, prefix='pretendientes')
        documento_formset = DocumentoFS(instance=rel, prefix='documentos')

    # Formsets de miembros por vivienda (prefijo dinámico miembros_viv_N)
    
    vivienda_miembro_formsets = {}
    miembro_template_formset = MiembroFS(prefix='miembros_viv_0')
    pret_vivienda_template_formset = ViviendaPretendienteFormSet(prefix='viviendas_pret_0')
    for i, viv_form in enumerate(vivienda_formset.forms):
        miem_prefix = f'miembros_viv_{i}'
        if request.method == 'POST' and f'{miem_prefix}-TOTAL_FORMS' in request.POST:
            vivienda_miembro_formsets[i] = MiembroFS(
                request.POST, request.FILES, prefix=miem_prefix
            )
        elif viv_form.instance.pk:
            vivienda_miembro_formsets[i] = MiembroFS(
                instance=viv_form.instance, prefix=miem_prefix
            )
        else:
            vivienda_miembro_formsets[i] = MiembroFS(prefix=miem_prefix)

    pretendiente_vivienda_formsets, pretendiente_miembro_formsets = _construir_formsets_pretendiente(
        request, pretendiente_formset, MiembroFS
    )

    context = {
        'form': form,
        'vivienda_formset': vivienda_formset,
        'vivienda_miembro_formsets': vivienda_miembro_formsets,
        'miembro_template_formset': miembro_template_formset,
        'cultivo_formset': cultivo_formset,
        'ganaderia_formset': ganaderia_formset,
        'institucion_formset': institucion_formset,
        'pretendiente_formset': pretendiente_formset,
        'pretendiente_vivienda_formsets': pretendiente_vivienda_formsets,
        'pretendiente_miembro_formsets': pretendiente_miembro_formsets,
        'pret_vivienda_template_formset': pret_vivienda_template_formset,
        'documento_formset': documento_formset,
        'relevamiento': rel,
        'orden': orden,
        'datos_geo': datos_geo,
        'title': f'Editar Relevamiento #{rel.pk}',
    }
    modo = _detectar_modo_relevamiento(rel)
    return render(request, TEMPLATE_MAP[modo], context)


# ─────────────────────────────────────────────
# FRACCIONAMIENTO: CREAR SUB-LOTE
# ─────────────────────────────────────────────

@login_required
@encuestador_required
def crear_sublote_fraccionamiento(request, pk):
    """
    Crea un nuevo sub-lote a partir de un Relevamiento en modo Fraccionamiento.
    Genera la nomenclatura secuencial automática (1A, 1B, 1C...) y redirige
    a su edición para completar los datos del sub-lote.
    """
    parent = get_object_or_404(Relevamiento, pk=pk)

    if request.method != 'POST':
        return redirect('relevamiento:resumen_relevamiento', pk=parent.pk)

    es_encuestador_asignado = parent.encuestador == request.user
    esta_en_equipo = parent.orden_trabajo.equipos_asignados.filter(encuestadores=request.user).exists()
    if not (es_encuestador_asignado or esta_en_equipo or request.user.is_superuser):
        messages.error(request, 'No tiene permisos para fraccionar este relevamiento.')
        return redirect('relevamiento:resumen_relevamiento', pk=parent.pk)

    try:
        sufijo = parent.siguiente_sufijo_sublote()
        sublote = Relevamiento.objects.create(
            orden_trabajo=parent.orden_trabajo,
            encuestador=request.user,
            departamento=parent.departamento,
            distrito=parent.distrito,
            colonia=parent.colonia,
            manzana=parent.manzana,
            lote_indert=f"{parent.lote_indert}{sufijo}",
            lote_sirt=f"{parent.lote_sirt}{sufijo}",
            tipo_registro='fraccionamiento',
            parent_lote=parent,
        )
        messages.success(request, f'Sub-lote {sublote.lote_indert} creado correctamente.')
        return redirect('relevamiento:edit', pk=sublote.pk)
    except Exception as e:
        messages.error(request, f'Error al crear el sub-lote: {str(e)}')
        return redirect('relevamiento:resumen_relevamiento', pk=parent.pk)


# ─────────────────────────────────────────────
# RESUMEN / DETALLE
# ─────────────────────────────────────────────

@login_required
def resumen_relevamiento(request, pk):
    """Muestra el detalle de un Relevamiento."""
    rel = get_object_or_404(Relevamiento, pk=pk)
    # La plantilla de resumen está en la carpeta de encuestador dentro de includes
    return render(request, 'includes/relevamiento/encuestador/resumen_relevamiento.html', {'relevamiento': rel})


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
                return _volver_al_resumen(rel)
            except Exception as e:
                messages.error(request, f'Error al subir fotos: {str(e)}')
    else:
        form = FotosRelevamientoForm()

    return render(request, 'relevamiento/agregar_fotos.html', {
        'form': form,
        'relevamiento': rel,
    })

def _volver_al_resumen(rel):
    """El flujo Ocupante usa el resumen nuevo; los demás modos siguen con el viejo."""
    if rel.tipo_registro == 'ocupante':
        return redirect('relevamiento:continuar_encuesta', pk=rel.pk, parte='encuesta')
    return redirect('relevamiento:resumen_relevamiento', pk=rel.pk)


