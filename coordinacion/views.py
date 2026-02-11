from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta

from gerencia.models import SolicitudRelevamiento
from coordinacion.models import EquipoRelevamiento, OrdenTrabajo, RegistroCampo
from coordinacion.decorators import coordinacion_required
from coordinacion.forms import GenerarOrdenForm, CrearEquipoForm


# ------------------ DASHBOARD SIMPLIFICADO ------------------ #
@login_required
@coordinacion_required
def dashboard_coordinacion(request):
    """
    Dashboard simplificado de coordinación
    """
    # Estadísticas básicas
    solicitudes_pendientes_count = SolicitudRelevamiento.objects.filter(
        estado='asignado_coordinacion'
    ).count()

    ordenes_activas_count = OrdenTrabajo.objects.filter(
        estado__in=['generada', 'asignada', 'en_proceso']
    ).count()

    equipos_campo_count = EquipoRelevamiento.objects.filter(
        activo=True,
        estado='en_campo'
    ).count()

    # Órdenes finalizadas este mes
    primer_dia_mes = timezone.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0)
    ordenes_finalizadas_mes = OrdenTrabajo.objects.filter(
        estado='completada',
        fecha_modificacion__gte=primer_dia_mes
    ).count()

    # Órdenes recientes (últimas 5)
    ordenes_recientes = OrdenTrabajo.objects.select_related(
        'solicitud', 'solicitud__colonia'
    ).prefetch_related('equipos_asignados').order_by('-fecha_creacion')[:5]

    # Solicitudes pendientes (para generar orden)
    solicitudes_pendientes = SolicitudRelevamiento.objects.filter(
        estado='asignado_coordinacion'
    ).select_related('colonia', 'creado_por').order_by('-prioridad', '-fecha_creacion')[:5]

    # Equipos disponibles para modales
    equipos_disponibles = EquipoRelevamiento.objects.filter(
        activo=True,
        estado__in=['planificado', 'en_campo']
    )

    context = {
        'solicitudes_pendientes_count': solicitudes_pendientes_count,
        'ordenes_activas_count': ordenes_activas_count,
        'equipos_campo_count': equipos_campo_count,
        'ordenes_finalizadas_mes': ordenes_finalizadas_mes,
        'ordenes_recientes': ordenes_recientes,
        'solicitudes_pendientes': solicitudes_pendientes,
        'equipos_disponibles': equipos_disponibles,
    }

    return render(request, 'coordinacion/coordinacion_dashboard.html', context)


# ------------------ GESTIÓN DE SOLICITUDES ------------------ #
@login_required
@coordinacion_required
def solicitudes_pendientes(request):
    """
    Lista simplificada de solicitudes pendientes
    """
    solicitudes = SolicitudRelevamiento.objects.filter(
        estado='asignado_coordinacion'
    ).select_related('colonia', 'creado_por').order_by('-prioridad', '-fecha_creacion')

    context = {
        'solicitudes': solicitudes,
        'total': solicitudes.count(),
    }

    return render(request, 'coordinacion/solicitudes_pendientes.html', context)


@login_required
@coordinacion_required
def generar_orden_view(request, solicitud_id):
    """
    Generar orden de trabajo (simplificado)
    """
    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)

    if solicitud.estado != 'asignado_coordinacion':
        messages.error(
            request, "Esta solicitud no está en estado válido para generar orden")
        return redirect('coordinacion:solicitudes_pendientes')

    if request.method == 'POST':
        form = GenerarOrdenForm(request.POST)
        if form.is_valid():
            orden = form.save(commit=False)
            orden.solicitud = solicitud
            orden.creado_por = request.user
            orden.coordinador_responsable = request.user

            # Generar número de orden
            if not orden.numero_orden:
                orden.numero_orden = f"OT-{timezone.now().strftime('%Y%m%d')}-{solicitud.id}"

            orden.save()

            # Actualizar estado de la solicitud
            solicitud.estado = 'orden_trabajo_generada'
            solicitud.numero_orden_trabajo = orden.numero_orden
            solicitud.fecha_generacion_orden = timezone.now()
            solicitud.usuario_generador_orden = request.user
            solicitud.save()

            messages.success(
                request, f'Orden {orden.numero_orden} generada exitosamente')
            return redirect('coordinacion:detalle_orden', orden_id=orden.id)
    else:
        # Valores por defecto
        fecha_inicio = timezone.now().date()
        fecha_fin = fecha_inicio + timedelta(days=7)

        form = GenerarOrdenForm(initial={
            'fecha_inicio_planeada': fecha_inicio,
            'fecha_fin_planeada': fecha_fin,
            'coordinador_responsable': request.user,
        })

    context = {
        'solicitud': solicitud,
        'form': form,
    }

    return render(request, 'coordinacion/generar_orden.html', context)


# ------------------ GESTIÓN DE ÓRDENES ------------------ #
@login_required
@coordinacion_required
def ordenes_trabajo(request):
    """
    Lista simplificada de órdenes
    """
    estado = request.GET.get('estado', 'activas')

    if estado == 'activas':
        ordenes = OrdenTrabajo.objects.filter(
            estado__in=['generada', 'asignada', 'en_proceso']
        )
    elif estado == 'todas':
        ordenes = OrdenTrabajo.objects.all()
    else:
        ordenes = OrdenTrabajo.objects.filter(estado=estado)

    ordenes = ordenes.select_related('solicitud', 'solicitud__colonia', 'coordinador_responsable'
                                     ).prefetch_related('equipos_asignados'
                                                        ).order_by('-fecha_creacion')

    context = {
        'ordenes': ordenes,
        'estado_actual': estado,
    }

    return render(request, 'coordinacion/ordenes_trabajo.html', context)


@login_required
@coordinacion_required
def detalle_orden(request, orden_id):
    """
    Detalle simplificado de orden
    """
    orden = get_object_or_404(
        OrdenTrabajo.objects.select_related(
            'solicitud', 'solicitud__colonia',
            'coordinador_responsable'
        ).prefetch_related('equipos_asignados'),
        id=orden_id
    )

    # Registros de campo recientes
    registros = RegistroCampo.objects.filter(
        orden_trabajo=orden
    ).select_related('equipo', 'registrado_por'
                     ).order_by('-fecha_registro', '-hora_inicio')[:10]

    context = {
        'orden': orden,
        'registros': registros,
    }

    return render(request, 'coordinacion/detalle_orden.html', context)


@login_required
@coordinacion_required
def asignar_equipos_orden(request, orden_id):
    """
    Asignar equipos a orden (simplificado)
    """
    orden = get_object_or_404(OrdenTrabajo, id=orden_id)

    if orden.estado != 'generada':
        messages.error(
            request, "Solo se pueden asignar equipos a órdenes en estado 'Generada'")
        return redirect('coordinacion:detalle_orden', orden_id=orden.id)

    if request.method == 'POST':
        equipos_ids = request.POST.getlist('equipos')

        if equipos_ids:
            equipos = EquipoRelevamiento.objects.filter(
                id__in=equipos_ids,
                activo=True
            )

            # Asignar equipos
            orden.equipos_asignados.set(equipos)

            # Actualizar estado de equipos
            equipos.update(estado='en_campo')

            # Actualizar estado de la orden
            orden.estado = 'asignada'
            orden.save()

            messages.success(
                request, f'{equipos.count()} equipos asignados exitosamente')
        else:
            messages.warning(request, "No se seleccionaron equipos")

    return redirect('coordinacion:detalle_orden', orden_id=orden.id)


# ------------------ GESTIÓN DE EQUIPOS ------------------ #
@login_required
@coordinacion_required
def equipos_relevamiento(request):
    """
    Lista simplificada de equipos
    """
    equipos = EquipoRelevamiento.objects.filter(
        activo=True
    ).select_related('coordinador_campo').order_by('nombre')

    context = {
        'equipos': equipos,
    }

    return render(request, 'coordinacion/equipos.html', context)


@login_required
@coordinacion_required
def crear_equipo(request):
    """
    Crear equipo (simplificado)
    """
    if request.method == 'POST':
        form = CrearEquipoForm(request.POST)
        if form.is_valid():
            equipo = form.save()
            messages.success(
                request, f'Equipo {equipo.nombre} creado exitosamente')
            return redirect('coordinacion:equipos_relevamiento')
    else:
        form = CrearEquipoForm(initial={'coordinador_campo': request.user})

    context = {'form': form}
    return render(request, 'coordinacion/crear_equipo.html', context)


# ------------------ REPORTES SIMPLIFICADOS ------------------ #
@login_required
@coordinacion_required
def reportes_coordinacion(request):
    """
    Reportes básicos
    """
    # Datos del último mes
    fecha_inicio = timezone.now() - timedelta(days=30)

    # Órdenes completadas
    ordenes_completadas = OrdenTrabajo.objects.filter(
        estado='completada',
        fecha_modificacion__gte=fecha_inicio
    ).select_related('solicitud', 'solicitud__colonia')

    # Estadísticas por equipo
    equipos = EquipoRelevamiento.objects.filter(activo=True)
    equipos_estadisticas = []

    for equipo in equipos:
        ordenes_equipo = ordenes_completadas.filter(equipos_asignados=equipo)
        equipos_estadisticas.append({
            'equipo': equipo,
            'ordenes_completadas': ordenes_equipo.count(),
        })

    context = {
        'ordenes_completadas': ordenes_completadas,
        'equipos_estadisticas': equipos_estadisticas,
        'total_ordenes': ordenes_completadas.count(),
        'periodo': 'Últimos 30 días',
    }

    return render(request, 'coordinacion/reportes.html', context)
