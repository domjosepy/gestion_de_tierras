from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count
from .models import ArchivoSubcoordinador
from django.utils import timezone as tz
from coordinacion.models import OrdenTrabajo
from .decorators import encuestador_required, coordinador_campo_required
from .models import Relevamiento, Documento, limpiar_nombre_carpeta
from .forms import RelevamientoForm, FotosRelevamientoForm
from django.db import transaction
from gerencia.models import SolicitudRelevamientoAudit, SolicitudRelevamiento
from administrador.models import Grupo
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.core.files.base import ContentFile
from PIL import Image
import os
import re
import json
import io



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
    for orden in ordenes:
        relevamientos_por_orden[orden.pk] = Relevamiento.objects.filter(
            orden_trabajo=orden,
            encuestador=request.user,
        ).count()

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
        cnt = relevamientos_por_orden.get(orden.pk, 0)
        meta = getattr(orden, 'meta_encuestas', 0) or 0
        progreso_percent = int(0 if meta == 0 else (cnt / meta) * 100)
        ordenes_context.append({
            'orden': orden,
            'estado_badge': m['badge'],
            'estado_icon': m['icon'],
            'relevamientos_count': cnt,
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
    
    # Verificar que el formulario esté habilitado por el coordinador de campo
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
        form = RelevamientoForm(request.POST, request.FILES, initial=initial)
        if form.is_valid():
            relevamiento = form.save(commit=False)
            # Forzar los datos geográficos de la orden (ignorar lo que envíe el form)
            relevamiento.colonia = datos_geo['colonia']
            relevamiento.distrito = datos_geo['distrito']
            relevamiento.departamento = datos_geo['departamento']
            relevamiento.orden_trabajo = orden
            relevamiento.encuestador = request.user
            relevamiento.save()
            form.save_m2m()
            messages.success(request, f'Relevamiento #{relevamiento.pk} creado correctamente.')
            return redirect(
                reverse('relevamiento:resumen_relevamiento', kwargs={'pk': relevamiento.pk})
            )
    else:
        form = RelevamientoForm(initial=initial)

    context = {
        'form': form,
        'title': f'Nueva Encuesta — {orden}',
        'orden': orden,
        'datos_geo': datos_geo,
    }
    return render(request, 'includes/relevamiento/encuestador/formulario_relevamiento.html', context)


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
    
    # Validar que el relevamiento tiene orden asociada
    if not rel.orden_trabajo:
        messages.error(request, 'Este relevamiento no tiene orden de trabajo asociada.')
        return redirect('relevamiento:encuestador_dashboard')
    
    orden = rel.orden_trabajo
    datos_geo = _datos_geograficos_desde_orden(orden)

    # Verificar que el usuario es el encuestador asignado o está en el equipo de la orden
    es_encuestador_asignado = rel.encuestador == request.user
    esta_en_equipo = orden.equipos_asignados.filter(encuestadores=request.user).exists()
    
    if not (es_encuestador_asignado or esta_en_equipo or request.user.is_superuser):
        messages.error(request, 'No tiene permisos para editar este relevamiento.')
        return redirect('relevamiento:encuestador_dashboard')

    if request.method == 'POST':
        form = RelevamientoForm(request.POST, request.FILES, instance=rel)
        if form.is_valid():
            relevamiento = form.save(commit=False)
            # Mantener los datos geográficos de la orden (no permitir cambios)
            relevamiento.colonia = datos_geo['colonia']
            relevamiento.distrito = datos_geo['distrito']
            relevamiento.departamento = datos_geo['departamento']
            relevamiento.orden_trabajo = orden
            relevamiento.save()
            form.save_m2m()
            messages.success(request, 'Relevamiento actualizado correctamente.')
            return redirect(
                reverse('relevamiento:resumen_relevamiento', kwargs={'pk': relevamiento.pk})
            )
    else:
        form = RelevamientoForm(instance=rel)

    context = {
        'form': form,
        'title': f'Editar Relevamiento #{rel.pk}',
        'relevamiento': rel,
        'orden': orden,
        'datos_geo': datos_geo,
    }
    return render(request, 'includes/relevamiento/encuestador/formulario_relevamiento.html', context)


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
   
    # Obtener todos los relevamientos del usuario actual
    relevamientos = Relevamiento.objects.filter(
        encuestador=request.user
    ).select_related(
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
            'manzana': rel.manzana or 'Sin datos',
            'loteSirt': rel.lote_sirt or 'Sin datos',
            'condicionVivienda': rel.get_condicion_vivienda_display() if rel.condicion_vivienda else 'Sin datos',
            'condicionEncuestado': rel.get_condicion_encuestado_display() if rel.condicion_encuestado else 'Sin datos',
            'quien_es_el_ocupante': rel.quien_es_el_ocupante or 'Sin información',
            'observaciones': rel.observacion_encuesta or 'Sin observaciones',
            'formularioHabilitado': rel.orden_trabajo.formulario_habilitado if rel.orden_trabajo else False,
        })
    
    context = {
        'relevamientos': relevamientos,
        'relevamientos_json': json.dumps(relevamientos_data, ensure_ascii=False),
    }
    return render(request, 'includes/relevamiento/encuestador/mis_encuestas.html', context)


@login_required
def agregar_fotos(request, pk):
    """Vista para agregar fotos a un relevamiento en 4 categorías.
    
    Maneja la subida de múltiples archivos por categoría (recibo, vivienda,
    documento, lote) y los guarda con un patrón de nombres específico:
    relevamiento_{manzana}_{lote_sirt}_{tipo_foto}_{indice}.jpg
    
    Los archivos se organizan en subcarpetas dentro de la colonia correspondiente.
    """

    rel = get_object_or_404(Relevamiento, pk=pk)
    
    if request.method == 'POST':
        form = FotosRelevamientoForm(request.POST, request.FILES)
        if form.is_valid():
            # Mapeo de campos a tipo de foto
            categorias = [
                ('fotos_recibo', 'recibo'),
                ('fotos_vivienda', 'vivienda'),
                ('fotos_documento', 'ci'),
                ('fotos_lote', 'lote'),
            ]
            
            # Preparar datos para nombres de archivo
            manzana = limpiar_nombre_carpeta(rel.manzana or 'sin_manzana')
            lote_sirt = limpiar_nombre_carpeta(rel.lote_sirt or 'sin_lote')
            
            total_archivos = 0
            
            # Procesar cada categoría
            for campo, tipo_foto in categorias:
                archivos = request.FILES.getlist(campo)
                
                for indice, archivo in enumerate(archivos, start=1):
                    try:
                        # Determinar extensión del archivo
                        ext = os.path.splitext(archivo.name)[1].lower()
                        if not ext:
                            ext = '.jpg'
                        
                        # Construir nombre del archivo según patrón
                        # relevamiento_{manzana}_{lote_sirt}_{tipo_foto}_{indice}.jpg
                        nombre_archivo = f"relevamiento_{manzana}_{lote_sirt}_{tipo_foto}_{indice}{ext}"
                        
                        # Convertir a JPG si es necesario (optimización opcional)
                        if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                            # Abrir imagen con Pillow para validar y opcionalmente convertir
                            try:
                                img = Image.open(archivo)
                                # Convertir a RGB si es necesario (para PNG con transparencia)
                                if img.mode in ('RGBA', 'LA', 'P'):
                                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                                    if img.mode == 'P':
                                        img = img.convert('RGBA')
                                    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                                    img = rgb_img
                                
                                # Guardar como JPG optimizado
                                buffer = io.BytesIO()
                                img.save(buffer, format='JPEG', quality=85, optimize=True)
                                buffer.seek(0)
                                
                                # Crear objeto ContentFile
                                content_file = ContentFile(buffer.read(), name=nombre_archivo)
                            except Exception as img_error:
                                # Si falla la conversión, usar el archivo original
                                print(f"Error al procesar imagen {archivo.name}: {img_error}")
                                archivo.seek(0)  # Resetear puntero del archivo
                                content_file = ContentFile(archivo.read(), name=nombre_archivo)
                        else:
                            # Para otros tipos de archivo, usar directamente
                            archivo.seek(0)
                            content_file = ContentFile(archivo.read(), name=nombre_archivo)
                        
                        # Crear registro de Documento
                        documento = Documento(
                            relevamiento=rel,
                            tipo=tipo_foto if tipo_foto in ['recibo'] else 'otros',
                            nombre_archivo=nombre_archivo
                        )
                        # Asignar el archivo procesado
                        documento.archivo.save(nombre_archivo, content_file, save=True)
                        
                        total_archivos += 1
                        
                    except Exception as e:
                        messages.warning(request, f'Error al procesar {archivo.name}: {str(e)}')
                        continue
            
            if total_archivos > 0:
                messages.success(request, f'Se subieron {total_archivos} foto(s) correctamente.')
            else:
                messages.info(request, 'No se seleccionaron archivos para subir.')
            
            return redirect(reverse('relevamiento:resumen_relevamiento', kwargs={'pk': rel.pk}))
    else:
        form = FotosRelevamientoForm()
    
    context = {
        'form': form,
        'relevamiento': rel,
    }
    return render(request, 'relevamiento/agregar_fotos.html', context)


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
        for equipo in equipos:
            subcoordinadores_count += equipo.subcoordinadores.count()
            encuestadores_count += equipo.encuestadores.count()
        
        # Contar relevamientos de esta orden
        relevamientos_count = Relevamiento.objects.filter(orden_trabajo=orden).count()
        
        ordenes_context.append({
            'orden': orden,
            'datos_geo': datos_geo,
            'subcoordinadores_count': subcoordinadores_count,
            'encuestadores_count': encuestadores_count,
            'relevamientos_count': relevamientos_count,
        })

    context = {
        'ordenes_context': ordenes_context,
        'total_ordenes': ordenes.count(),
    }
    return render(request, 'relevamiento/coordinador_dashboard.html', context)


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
    total_archivos = 0
    ordenes_completadas = 0
    ordenes_en_proceso = 0
    
    for orden in ordenes:
        colonia = orden.solicitud.colonia if orden.solicitud else None
        if not colonia:
            continue
        
        # Contar relevamientos de esta orden
        relevamientos_count = Relevamiento.objects.filter(orden_trabajo=orden).count()
        total_relevamientos += relevamientos_count
        
        # Contar archivos subidos para esta orden
        from .models import ArchivoSubcoordinador
        archivos_count = ArchivoSubcoordinador.objects.filter(orden_trabajo=orden).count()
        total_archivos += archivos_count
        
        # Obtener el archivo más reciente
        archivo_reciente = ArchivoSubcoordinador.objects.filter(orden_trabajo=orden).first()
        
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
                'archivo_url': archivo_reciente.archivo.url if archivo_reciente else None,
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
                'archivos_count': archivos_count,
                # habilitar_subida se controla por la orden (formulario_habilitado)
                'habilitar_subida': bool(orden.formulario_habilitado),
            }

    colonias = list(colonias_map.values())

    return render(request, 'relevamiento/subcoordinador_dashboard.html', {
        'colonias': colonias,
        'total_ordenes': ordenes.count(),
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
                orden.save()
                
                # Asignar solicitud al grupo de análisis
                try:
                    grupo_analisis = Grupo.objects.filter(
                        nombre__icontains='ANALISIS',
                        activo=True
                    ).first()
                    # PARA MEJOR ESCLARECIMIENTO DEL FLUJO, UNA VEZ QUE LA COLONIA SE TERMINA
                    # 1. EL ESTADO PASA A FINALIZADO: EN ESTE ESTADO SE ENCUENTRA LA SOLICITUD 
                    # CUANDO EL COORDINADOR DE CAMPO FINALIZA LA ORDEN DE TRABAJO, PERO ANTES 
                    # DE REASIGNARLA AL GRUPO DE ANALISIS. EN ESTE ESTADO, LA SOLICITUD NO PUEDE SER 
                    # REABIERTO POR EL COORDINADOR DE CAMPO, NI ASIGNADA A UN NUEVO EQUIPO DE CAMPO. 
                    # SOLO EL GRUPO DE ANALISIS PUEDE VER LAS SOLICITUDES EN ESTADO FINALIZADO 
                    # Y ASIGNARLAS A UN ANALISTA PARA SU PROCESAMIENTO.
                    if grupo_analisis:
                        solicitud.estado = 'finalizado'

                        # Marcar la solicitud según su tipo como terminada
                        if solicitud.tipo == SolicitudRelevamiento.TIPO_RELEVAMIENTO:
                            solicitud.relevamiento_terminado = True
                            
                        elif solicitud.tipo == SolicitudRelevamiento.TIPO_ACTUALIZACION:
                            solicitud.actualizacion_terminado = True
                        solicitud.grupo_asignado = grupo_analisis
                        solicitud.usuario_asignado = None
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
    
    # Resumen por encuestador
    encuestadores_stats = []
    for encuestador in encuestadores:
        # Contar encuestas en esta colonia por este encuestador
        total_encuestas = Relevamiento.objects.filter(
            encuestador=encuestador,
            colonia=datos_geo['colonia']
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
    
    # Total de solicitudes en la colonia
    total_solicitudes = SolicitudRelevamiento.objects.filter(
        colonia=datos_geo['colonia']
    ).count() if datos_geo['colonia'] else 0
    
    context = {
        'orden': orden,
        'datos_geo': datos_geo,
        'subcoordinadores': subcoordinadores,
        'encuestadores': encuestadores,
        'encuestadores_stats': encuestadores_stats,
        'subcoordinadores_stats': subcoordinadores_stats,
        'total_solicitudes': total_solicitudes,
    }
    
    return render(request, 'includes/relevamiento/coordinador/detalle_relevamiento.html', context)


