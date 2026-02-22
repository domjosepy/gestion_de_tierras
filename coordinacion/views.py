# 1. Librerías estándar de Python
import json
from datetime import datetime, timedelta

# 2. Django Core (HTTP, Shortcuts, Auth, etc.)
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Max
from django.db.models import Prefetch

# 3. Aplicaciones locales (Tus modelos, decoradores y formularios)
from administrador.models import User, Grupo
from gerencia.models import SolicitudRelevamiento, SolicitudRelevamientoAudit
from coordinacion.models import EquipoRelevamiento, OrdenTrabajo, RegistroCampo
from coordinacion.decorators import coordinacion_required, lider_coordinacion_required
from coordinacion.forms import (GenerarOrdenForm, CrearEquipoForm,
                                UsuarioPorGrupoField, UsuarioPorGrupoSimpleField)
from coordinacion.utils import contar_dias_habiles


# ------------------ DASHBOARD SIMPLIFICADO ------------------ #


@login_required
@coordinacion_required
def dashboard_coordinacion(request):
    """
    Dashboard simplificado de coordinación
    """
    ordenes_activas_count = OrdenTrabajo.objects.filter(
        estado__in=['generada', 'asignada', 'en_proceso']
    ).count()

    equipos_campo_count = EquipoRelevamiento.objects.filter(
        activo=True,
        estado='en_campo'
    ).count()

    solicitudes_canceladas_count = SolicitudRelevamiento.objects.filter(
        ordenes_trabajo__estado='cancelada'
    ).distinct().count()

    # Órdenes finalizadas este mes
    primer_dia_mes = timezone.now().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    ordenes_finalizadas_mes = OrdenTrabajo.objects.filter(
        estado='completada',
        fecha_modificacion__gte=primer_dia_mes
    ).count()

    # Órdenes recientes (últimas 5)[:5]
    ordenes_recientes = OrdenTrabajo.objects.exclude(
        estado__in=['reactivado', 'cancelada']
    ).select_related(
        'solicitud', 'solicitud__colonia', 'solicitud__coordinador_campo'
    ).prefetch_related('equipos_asignados').order_by('-fecha_creacion')

    # Solicitudes pendientes (para generar orden)
    solicitudes_pendientes = SolicitudRelevamiento.objects.filter(
        estado='asignado_coordinacion'
    ).exclude(
        ordenes_trabajo__activa=False
    ).select_related('colonia', 'creado_por').order_by('-prioridad', '-fecha_creacion')

    # Estadísticas básicas
    solicitudes_pendientes_count = solicitudes_pendientes.count()

    # Equipos disponibles para modales
    equipos_disponibles = EquipoRelevamiento.objects.filter(
        activo=True,
        estado__in=['planificado', 'en_campo']
    )

    # Usuarios por rol
    coordinadores = User.objects.filter(
        groups__name__icontains='Rol_COORDINADOR', is_active=True
    ).order_by('username')
    subcoordinadores = User.objects.filter(
        groups__name__icontains='Rol_SUBCOORDINADOR', is_active=True
    ).order_by('username')
    encuestadores = User.objects.filter(
        groups__name__icontains='Rol_ENCUESTADOR', is_active=True
    ).order_by('username')
    choferes = User.objects.filter(
        groups__name__icontains='Rol_CHOFER', is_active=True
    ).order_by('username')

    # Context completo
    context = {
        'solicitudes_pendientes_count': solicitudes_pendientes_count,
        'ordenes_activas_count': ordenes_activas_count,
        'equipos_campo_count': equipos_campo_count,
        'solicitudes_canceladas_count': solicitudes_canceladas_count,
        'ordenes_finalizadas_mes': ordenes_finalizadas_mes,
        'ordenes_recientes': ordenes_recientes,
        'solicitudes_pendientes': solicitudes_pendientes,
        'equipos_disponibles': equipos_disponibles,
        'coordinadores': coordinadores,
        'subcoordinadores': subcoordinadores,
        'encuestadores': encuestadores,
        'choferes': choferes,
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
    ).exclude(
        ordenes_trabajo__activa=True
    ).select_related('colonia', 'creado_por').order_by('-prioridad', '-fecha_creacion')

    context = {
        'solicitudes': solicitudes,
        'total': solicitudes.count(),
    }

    return render(request, 'includes/coordinacion/solicitudes_relevamiento/solicitudes_pendientes.html', context)


@login_required
@coordinacion_required
def solicitudes_canceladas(request):
    solicitudes = SolicitudRelevamiento.objects.filter(
        ordenes_trabajo__estado='cancelada'
    ).distinct().prefetch_related(
        Prefetch(
            'ordenes_trabajo',
            queryset=OrdenTrabajo.objects.filter(
                estado='cancelada').order_by('-fecha_modificacion'),
            to_attr='ordenes_canceladas'
        )
    ).select_related('colonia', 'creado_por').order_by('-ordenes_trabajo__fecha_modificacion')

    context = {
        'solicitudes': solicitudes,
        'total': solicitudes.count(),
    }
    return render(request, 'includes/coordinacion/solicitudes_relevamiento/solicitudes_canceladas.html', context)


@login_required
@coordinacion_required
def generar_orden_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)

    if solicitud.estado != 'asignado_coordinacion':
        messages.error(
            request, "La solicitud no está en estado válido para generar orden.")
        return redirect('coordinacion:solicitudes_pendientes')

    if solicitud.ordenes_trabajo.filter(activa=True).exists():
        messages.info(request, "Esta solicitud ya tiene una orden activa.")
        return redirect('coordinacion:detalle_orden', orden_id=solicitud.ordenes_trabajo.get(activa=True).id)

    if request.method == 'POST':
        form = GenerarOrdenForm(request.POST, request=request)
        if form.is_valid():
            with transaction.atomic():
                OrdenTrabajo.objects.filter(
                    solicitud=solicitud, activa=True).update(activa=False)

                # Crear orden
                orden = form.save(commit=False)
                orden.solicitud = solicitud
                orden.creado_por = request.user
                orden.activa = True
                orden.save()

                # 2. Actualizar solicitud
                solicitud.estado = 'orden_trabajo_generada'
                solicitud.numero_orden_trabajo = orden.numero_orden
                solicitud.fecha_generacion_orden = timezone.now()
                solicitud.usuario_generador_orden = request.user
                solicitud.save()

                # 3. Asignar equipo de campo a la solicitud
                coordinador = form.cleaned_data.get('coordinador_campo')
                subcoordinadores = form.cleaned_data.get('subcoordinadores')
                encuestadores = form.cleaned_data.get('encuestadores')
                choferes = form.cleaned_data.get('choferes')

                # Asignar los campos a la solicitud
                if coordinador:
                    solicitud.coordinador_campo = coordinador
                if subcoordinadores is not None:
                    solicitud.subcoordinadores.set(subcoordinadores)
                if choferes is not None:
                    solicitud.choferes.set(choferes)
                if encuestadores is not None:
                    # Usamos el método existente asignar_relevadores que cambia estado a 'asignado_relevadores'
                    solicitud.asignar_relevadores(
                        encuestadores, request.user, "Asignado al generar orden")

                # Guardar cambios en solicitud (el método asignar_relevadores ya hace save, pero por si acaso)
                solicitud.save()

                # 4. Crear equipo de relevamiento (opcional, pero útil)
                if coordinador or subcoordinadores or encuestadores or choferes:
                    equipo = EquipoRelevamiento.objects.create(
                        nombre=f"Equipo OT-{orden.numero_orden}",
                        tipo='completo',
                        estado='planificado',
                        coordinador_campo=coordinador or request.user,
                        activo=True,
                        max_encuestadores=4,
                    )
                    if subcoordinadores:
                        equipo.subcoordinadores.set(subcoordinadores)
                    if encuestadores:
                        equipo.encuestadores.set(encuestadores)
                    if choferes:
                        equipo.choferes.set(choferes)
                    # Asociar equipo a la orden
                    orden.equipos_asignados.add(equipo)
                    orden.estado = 'asignada'
                    # Antes de crear la nueva orden
                    OrdenTrabajo.objects.filter(
                        solicitud=solicitud, activa=True).update(activa=False)
                    orden.save()

                # 5. Auditoría adicional (puede ser manejada por signals o manual)
                # (Opcional: registrar en SolicitudRelevamientoAudit los cambios en los campos de equipo)

                messages.success(
                    request, f'Orden {orden.numero_orden} generada exitosamente.')
                return redirect('coordinacion:detalle_orden', orden_id=orden.id)
    else:
        form = GenerarOrdenForm(request=request)

    context = {
        'solicitud': solicitud,
        'form': form,
    }
    return render(request, 'includes/coordinacion/orden_trabajo/generar_orden.html', context)

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

    return render(request, 'includes/coordinacion/orden_trabajo/ordenes_trabajo.html', context)


@login_required
@coordinacion_required
def detalle_orden(request, orden_id):
    """
    Detalle simplificado de orden
    """
    orden = get_object_or_404(
        OrdenTrabajo.objects.select_related(
            'solicitud', 'solicitud__colonia', 'solicitud__coordinador_campo',
            'coordinador_responsable'
        ).prefetch_related(
            'equipos_asignados',
            'solicitud__subcoordinadores',
            'solicitud__relevadores_asignados',
            'solicitud__choferes'
        ),
        id=orden_id
    )

    # Registros de campo recientes
    registros = RegistroCampo.objects.filter(
        orden_trabajo=orden
    ).select_related('equipo', 'registrado_por'
                     ).order_by('-fecha_registro', '-hora_inicio')[:10]
    # Usuarios por rol
    coordinadores = User.objects.filter(
        groups__name__icontains='Rol_COORDINADOR', is_active=True
    ).order_by('username')
    subcoordinadores = User.objects.filter(
        groups__name__icontains='Rol_SUBCOORDINADOR', is_active=True
    ).order_by('username')
    encuestadores = User.objects.filter(
        groups__name__icontains='Rol_ENCUESTADOR', is_active=True
    ).order_by('username')
    choferes = User.objects.filter(
        groups__name__icontains='Rol_CHOFER', is_active=True
    ).order_by('username')

    context = {
        'orden': orden,
        'registros': registros,
        'coordinadores': coordinadores,
        'subcoordinadores': subcoordinadores,
        'encuestadores': encuestadores,
        'choferes': choferes,
    }

    return render(request, 'includes/coordinacion/orden_trabajo/detalle_orden.html', context)


@login_required
@coordinacion_required
def asignar_equipos_orden(request, orden_id):
    """
    Asignar equipos a orden
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


@login_required
@lider_coordinacion_required
def modificar_orden(request, orden_id):
    """
    Modifica una orden existente: fechas y equipo de campo.
    Solo permitido si la orden no está completada ni cancelada.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    orden = get_object_or_404(OrdenTrabajo, id=orden_id)
    solicitud = orden.solicitud

    # Verificar estados permitidos
    if orden.estado in ['completada', 'cancelada']:
        return JsonResponse({'success': False, 'message': 'No se puede modificar una orden completada o cancelada.'}, status=400)

    # Verificar que el usuario es líder del grupo asignado
    if not (solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user):
        return JsonResponse({'success': False, 'message': 'No tiene permisos de líder para modificar esta orden.'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Datos JSON inválidos'}, status=400)

    # Extraer campos
    fecha_inicio = data.get('fecha_inicio_planeada')
    fecha_fin = data.get('fecha_fin_planeada')
    coordinador_id = data.get('coordinador_campo')
    subcoordinador_ids = data.get('subcoordinadores', [])
    encuestador_ids = data.get('encuestadores', [])
    chofer_ids = data.get('choferes', [])
    comentario = data.get('comentario', '')

    # Validaciones básicas
    if not fecha_inicio or not fecha_fin:
        return JsonResponse({'success': False, 'message': 'Las fechas son obligatorias.'}, status=400)

    from django.utils.dateparse import parse_date
    fecha_inicio_obj = parse_date(fecha_inicio)
    fecha_fin_obj = parse_date(fecha_fin)

    if not fecha_inicio_obj or not fecha_fin_obj:
        return JsonResponse({'success': False, 'message': 'Formato de fecha inválido.'}, status=400)

    # Validar rango de días hábiles
    hoy = timezone.now().date()
    if fecha_inicio_obj < hoy:
        return JsonResponse({'success': False, 'message': 'La fecha de inicio no puede ser pasada.'}, status=400)
    if fecha_inicio_obj.weekday() >= 5:
        return JsonResponse({'success': False, 'message': 'La fecha de inicio debe ser día hábil (Lunes a Viernes).'}, status=400)
    if fecha_fin_obj.weekday() >= 5:
        return JsonResponse({'success': False, 'message': 'La fecha de fin debe ser día hábil (Lunes a Viernes).'}, status=400)

    temp_form = GenerarOrdenForm()
    dias_habiles = contar_dias_habiles(fecha_inicio_obj, fecha_fin_obj)
    if dias_habiles < 1 or dias_habiles > 5:
        return JsonResponse({'success': False, 'message': f'El período debe ser de 1 a 5 días hábiles (actual: {dias_habiles}).'}, status=400)

    # Función para validar usuarios por rol

    def validar_usuario(user_id, rol):
        if not user_id:
            return None
        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise ValidationError(f'Usuario con id {user_id} no encontrado.')
        if not user.groups.filter(name__icontains=rol).exists():
            raise ValidationError(
                f'El usuario {user.username} no tiene el rol {rol}.')
        return user

    try:
        coordinador = validar_usuario(
            coordinador_id, 'Coordinador') if coordinador_id else None
        subcoordinadores = [validar_usuario(
            uid, 'Subcoordinador') for uid in subcoordinador_ids if uid]
        encuestadores = [validar_usuario(uid, 'Encuestador')
                         for uid in encuestador_ids if uid]
        choferes = [validar_usuario(uid, 'Chofer')
                    for uid in chofer_ids if uid]
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    # Actualizar en transacción atómica
    try:
        with transaction.atomic():
            # Guardar valores anteriores para auditoría
            fechas_anteriores = f"{orden.fecha_inicio_planeada} - {orden.fecha_fin_planeada}"
            coordinador_anterior = solicitud.coordinador_campo
            subcoordinadores_anteriores = list(
                solicitud.subcoordinadores.all())
            encuestadores_anteriores = list(
                solicitud.relevadores_asignados.all())
            choferes_anteriores = list(solicitud.choferes.all())

            orden.estado = 'asignada'
            # Actualizar fechas de la orden
            orden.fecha_inicio_planeada = fecha_inicio_obj
            orden.fecha_fin_planeada = fecha_fin_obj
            orden.save()

            # Actualizar equipo en la solicitud
            solicitud.estado = 'asignado_relevadores'
            solicitud.coordinador_campo = coordinador
            solicitud.subcoordinadores.set(subcoordinadores)
            solicitud.choferes.set(choferes)
            solicitud.relevadores_asignados.set(encuestadores)
            solicitud.save()
            # Auditoría general (puedes detallar más si quieres)
            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='modificacion_orden',
                valor_anterior=f"Fechas: {fechas_anteriores}",
                valor_nuevo=f"Fechas: {fecha_inicio_obj} - {fecha_fin_obj}",
                cambiado_por=request.user,
                comentario=comentario or f"Modificación por {request.user.username}"
            )

            return JsonResponse({
                'success': True,
                'message': 'Orden modificada exitosamente.'
            })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al modificar: {str(e)}'}, status=500)


@login_required
@lider_coordinacion_required
def cancelar_orden(request, orden_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    orden = get_object_or_404(OrdenTrabajo, id=orden_id)
    solicitud = orden.solicitud

    # Verificar estados permitidos
    if orden.estado not in ['generada', 'asignada']:
        return JsonResponse({'error': 'Solo se pueden cancelar órdenes en estado Generada o Asignada.'}, status=400)

    # Verificar permisos de líder
    if not (solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user):
        return JsonResponse({'error': 'No tiene permisos de líder para cancelar esta orden.'}, status=403)

    try:
        # Leer el motivo del cuerpo JSON
        data = json.loads(request.body) if request.body else {}
        motivo = data.get('motivo_cancelacion', '')

        with transaction.atomic():
            # Cancelar la orden y desactivar
            orden.estado = 'cancelada'
            orden.activa = False
            orden.motivo_cancelacion = motivo
            orden.save()

            solicitud.estado = 'asignado_coordinacion'
            solicitud.numero_orden_trabajo = None
            solicitud.fecha_generacion_orden = None
            solicitud.usuario_generador_orden = None
            solicitud.coordinador_campo = None
            solicitud.subcoordinadores.clear()
            solicitud.relevadores_asignados.clear()
            solicitud.choferes.clear()
            solicitud.save()

            equipo = orden.equipos_asignados.first()
            if equipo:
                equipo.activo = False
                equipo.save()

            # 4. Auditoría con motivo incluido
            comentario = f"Orden cancelada por {request.user.username}"
            if motivo:
                comentario += f". Motivo: {motivo}"
            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='cancelacion_orden',
                valor_anterior=f"Orden {orden.numero_orden}",
                valor_nuevo='Cancelado',
                cambiado_por=request.user,
                comentario=comentario
            )

        return JsonResponse({'success': True, 'message': 'Orden cancelada correctamente.'})
    except Exception as e:
        return JsonResponse({'error': f'Error al cancelar: {str(e)}'}, status=500)


@login_required
@lider_coordinacion_required
def reactivar_orden(request, orden_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    orden = get_object_or_404(OrdenTrabajo, id=orden_id, estado='cancelada')
    solicitud = orden.solicitud

    # Verificar permisos de líder
    if not (solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user):
        return JsonResponse({'error': 'No tiene permisos de líder para reactivar esta orden.'}, status=403)

    # Verificar que no haya otra orden activa para la misma solicitud
    if solicitud.ordenes_trabajo.filter(activa=True).exists():
        return JsonResponse({'error': 'La solicitud ya tiene una orden activa. No se puede reactivar esta.'}, status=400)

    try:
        with transaction.atomic():
            # Reactivar la orden
            orden.activa = True
            orden.estado = 'reactivado'
            orden.save()

            # Restaurar en la solicitud los campos de orden
            # si había relevadores, o 'orden_trabajo_generada' si no
            solicitud.estado = 'asignado_coordinacion'
            solicitud.numero_orden_trabajo = orden.numero_orden
            solicitud.fecha_generacion_orden = orden.fecha_creacion
            solicitud.usuario_generador_orden = orden.creado_por
            # Restaurar equipo si estaba en la orden (asumiendo que la orden tiene equipo asociado)
            equipo = orden.equipos_asignados.first()
            if equipo:
                equipo.activo = True
                equipo.save()
            solicitud.save()

            # Auditoría
            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='reactivacion_orden',
                valor_anterior='cancelada',
                valor_nuevo='activa',
                cambiado_por=request.user,
                comentario=f"Orden reactivada por: {request.user.username}"
            )

        return JsonResponse({'success': True, 'message': 'Orden reactivada correctamente.'})
    except Exception as e:
        return JsonResponse({'error': f'Error al reactivar: {str(e)}'}, status=500)

# ------------------ REPORTES SIMPLIFICADOS ------------------ #


@login_required
@coordinacion_required
def reportes_coordinacion(request):
    # Obtener fechas de filtro (si vienen por GET)
    fecha_desde = request.GET.get('desde')
    fecha_hasta = request.GET.get('hasta')

    if fecha_desde and fecha_hasta:
        desde = timezone.datetime.strptime(fecha_desde, '%Y-%m-%d').date()
        hasta = timezone.datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
    else:
        hasta = timezone.now().date()
        desde = hasta - timedelta(days=30)

    # Filtrar órdenes completadas en el rango
    ordenes_completadas = OrdenTrabajo.objects.filter(
        estado='completada',
        fecha_modificacion__date__gte=desde,
        fecha_modificacion__date__lte=hasta
    ).select_related('solicitud__colonia').prefetch_related('equipos_asignados')

    # Estadísticas generales
    total_ordenes = ordenes_completadas.count()
    total_encuestas = ordenes_completadas.aggregate(Sum('encuestas_completadas'))[
        'encuestas_completadas__sum'] or 0

    # Calcular promedio de duración manualmente (duracion_planeada es propiedad)
    if total_ordenes > 0:
        suma_dias = 0
        for orden in ordenes_completadas:
            suma_dias += (orden.fecha_fin_planeada -
                          orden.fecha_inicio_planeada).days
        promedio_duracion = suma_dias / total_ordenes
    else:
        promedio_duracion = 0

    # Órdenes por estado (para gráfico de torta)
    estados = list(OrdenTrabajo.objects.values(
        'estado').annotate(cantidad=Count('id')))

    # Encuestas por equipo (para gráfico de barras)
    equipos = EquipoRelevamiento.objects.filter(activo=True)
    datos_equipos = []
    for equipo in equipos:
        ordenes_equipo = ordenes_completadas.filter(equipos_asignados=equipo)
        datos_equipos.append({
            'nombre': equipo.nombre,
            'ordenes': ordenes_equipo.count(),
            'encuestas': ordenes_equipo.aggregate(Sum('encuestas_completadas'))['encuestas_completadas__sum'] or 0
        })

    context = {
        'ordenes_completadas': ordenes_completadas[:20],
        'total_ordenes': total_ordenes,
        'total_encuestas': total_encuestas,
        'promedio_duracion': round(promedio_duracion, 1),
        'estados': estados,
        'datos_equipos': datos_equipos,
        'desde': desde,
        'hasta': hasta,
    }
    return render(request, 'includes/coordinacion/coordinacion_reportes.html', context)

# =========


@login_required
@coordinacion_required
def asignar_personal_orden(request, orden_id):
    """
    Asigna personal (coordinador, subcoordinadores, encuestadores, choferes)
    a una orden en estado 'generada'. Crea un equipo automáticamente y
    actualiza la solicitud asociada.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    orden = get_object_or_404(OrdenTrabajo, id=orden_id, estado='generada')
    solicitud = orden.solicitud

    # Si la petición es AJAX, esperamos JSON; si es POST normal, usamos request.POST
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)
    else:
        data = request.POST

    # Obtener IDs de los campos
    coordinador_id = data.get('coordinador_campo')
    sub_ids = data.getlist('subcoordinadores') if hasattr(
        data, 'getlist') else data.get('subcoordinadores', [])
    enc_ids = data.getlist('encuestadores') if hasattr(
        data, 'getlist') else data.get('encuestadores', [])
    chofer_ids = data.getlist('choferes') if hasattr(
        data, 'getlist') else data.get('choferes', [])
    comentario = data.get('comentario', '')

    # Validar que haya al menos coordinador
    if not coordinador_id:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Debe seleccionar un coordinador de campo'}, status=400)
        else:
            messages.error(request, 'Debe seleccionar un coordinador de campo')
            return redirect('coordinacion:coordinacion_dashboard')

    # Función auxiliar para validar usuario y rol
    def validar_usuario(user_id, rol):
        try:
            user = User.objects.get(id=user_id, is_active=True)
            if not user.groups.filter(name__icontains=rol).exists():
                return None, f'El usuario {user.username} no tiene el rol {rol}'
            return user, None
        except User.DoesNotExist:
            return None, 'Usuario no encontrado'

    # Validar coordinador
    coordinador, error = validar_usuario(coordinador_id, 'Rol_COORDINADOR')
    if error:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': error}, status=400)
        else:
            messages.error(request, error)
            return redirect('coordinacion:coordinacion_dashboard')

    # Validar subcoordinadores
    subcoordinadores = []
    for uid in sub_ids:
        u, e = validar_usuario(uid, 'Rol_SUBCOORDINADOR')
        if e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': e}, status=400)
            else:
                messages.error(request, e)
                return redirect('coordinacion:coordinacion_dashboard')
        subcoordinadores.append(u)

    # Validar encuestadores
    encuestadores = []
    for uid in enc_ids:
        u, e = validar_usuario(uid, 'Rol_ENCUESTADOR')
        if e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': e}, status=400)
            else:
                messages.error(request, e)
                return redirect('coordinacion:coordinacion_dashboard')
        encuestadores.append(u)

    # Validar choferes
    choferes = []
    for uid in chofer_ids:
        u, e = validar_usuario(uid, 'Rol_CHOFER')
        if e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': e}, status=400)
            else:
                messages.error(request, e)
                return redirect('coordinacion:coordinacion_dashboard')
        choferes.append(u)

    # Transacción atómica
    try:
        with transaction.atomic():
            # Actualizar la solicitud
            solicitud.coordinador_campo = coordinador
            solicitud.subcoordinadores.set(subcoordinadores)
            solicitud.choferes.set(choferes)

            # Asignar encuestadores directamente (sin usar asignar_relevadores)
            solicitud.relevadores_asignados.set(encuestadores)

            # Auditoría para encuestadores (similar a las otras)
            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='relevadores_asignados',
                valor_anterior=', '.join(
                    [u.username for u in solicitud.relevadores_asignados.all()]) or 'Ninguno',
                valor_nuevo=', '.join(
                    [u.username for u in encuestadores]) or 'Ninguno',
                cambiado_por=request.user,
                comentario=comentario or f"Asignación de encuestadores por {request.user.username}"
            )

            solicitud.save()

            # Crear el equipo (igual que antes)
            equipo = EquipoRelevamiento.objects.create(
                nombre=f"Equipo OT-{orden.numero_orden}",
                tipo='completo',
                estado='planificado',
                coordinador_campo=coordinador,
                activo=True,
                max_encuestadores=4,
            )
            if subcoordinadores:
                equipo.subcoordinadores.set(subcoordinadores)
            if encuestadores:
                equipo.encuestadores.set(encuestadores)
            if choferes:
                equipo.choferes.set(choferes)

            orden.equipos_asignados.add(equipo)
            orden.estado = 'asignada'
            orden.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Personal asignado correctamente'})
        else:
            messages.success(request, 'Personal asignado correctamente')
            return redirect('coordinacion:coordinacion_dashboard')
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': f'Error al asignar: {str(e)}'}, status=500)
        else:
            messages.error(request, f'Error al asignar: {str(e)}')
            return redirect('coordinacion:coordinacion_dashboard')
