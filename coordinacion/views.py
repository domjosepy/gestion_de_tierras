# 1. Librerías estándar de Python
import json
from datetime import datetime, timedelta

# 2. Django Core (HTTP, Shortcuts, Auth, etc.)
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count
from django.forms import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone

# 3. Aplicaciones locales (Tus modelos, decoradores y formularios)
from administrador.models import User, Grupo
from gerencia.models import SolicitudRelevamiento, SolicitudRelevamientoAudit
from coordinacion.models import EquipoRelevamiento, OrdenTrabajo, RegistroCampo
from coordinacion.decorators import coordinacion_required, lider_coordinacion_required
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

    return render(request, 'includes/coordinacion/solicitudes_relevamiento/solicitudes_pendientes.html', context)


@login_required
@coordinacion_required
def generar_orden_view(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)

    if solicitud.estado != 'asignado_coordinacion':
        messages.error(
            request, "La solicitud no está en estado válido para generar orden.")
        return redirect('coordinacion:solicitudes_pendientes')

    if request.method == 'POST':
        form = GenerarOrdenForm(request.POST, request=request)
        if form.is_valid():
            with transaction.atomic():
                # 1. Crear orden
                orden = form.save(commit=False)
                orden.solicitud = solicitud
                orden.creado_por = request.user
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
                    # Opcional: cambiar estado de la orden a 'asignada'
                    orden.estado = 'asignada'
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
@lider_coordinacion_required  # Solo líderes de coordinación
def asignar_equipo_campo(request, solicitud_id):
    """
    Asigna equipo de campo completo a una solicitud:

    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)

    # --- 1. Validar estado permitido ---
    estados_permitidos = ['aprobado_para_campo', 'asignado_coordinacion']
    if solicitud.estado not in estados_permitidos:
        return JsonResponse({
            'error': f'La solicitud debe estar en {", ".join(estados_permitidos)}. Estado actual: {solicitud.get_estado_display()}'
        }, status=400)

    # --- 2. Verificar que el usuario es líder del grupo asignado (Coordinación) ---
    # Asumimos que el grupo asignado es de coordinación
    if not (solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user):
        return JsonResponse({
            'error': 'No tiene permisos de líder del grupo asignado para realizar esta acción.'
        }, status=403)

    # --- 3. Leer datos JSON ---
    try:
        data = json.loads(request.body)
        coordinador_id = data.get('coordinador_id')
        subcoordinador_ids = data.get('subcoordinador_ids', [])
        encuestador_ids = data.get('encuestador_ids', [])
        chofer_ids = data.get('chofer_ids', [])
        comentario = data.get('comentario', '')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)

    # --- 4. Validar que al menos hay un coordinador (obligatorio) ---
    if not coordinador_id:
        return JsonResponse({'error': 'Debe asignar un coordinador de campo.'}, status=400)

    # --- 5. Obtener los usuarios y validar que pertenezcan al grupo "relevamiento" y tengan el rol adecuado ---
    # Definimos los nombres de grupos/subgrupos según tu esquema. Ajusta según tu implementación.
    # Aquí asumimos que existen grupos: "Coordinador", "Subcoordinador", "Encuestador", "Chofer" dentro del grupo "Relevamiento".
    # O bien, puedes usar un campo de perfil (Profile.rol). Adapta esta lógica a tu caso.

    def validar_usuario(user_id, grupo_rol):
        """Verifica que el usuario existe, está activo y pertenece al grupo de rol indicado."""
        if not user_id:
            return None
        usuario = get_object_or_404(User, id=user_id, is_active=True)
        # Verificar que pertenece al grupo "relevamiento" (o al grupo padre) y al subgrupo específico
        # Método 1: grupos de Django
        if not usuario.groups.filter(name__icontains='relevamiento').exists():
            raise ValidationError(
                f'El usuario {usuario.username} no pertenece al grupo Relevamiento.')
        if not usuario.groups.filter(name__icontains=grupo_rol).exists():
            raise ValidationError(
                f'El usuario {usuario.username} no tiene el rol {grupo_rol}.')
        return usuario

    try:
        coordinador = validar_usuario(coordinador_id, 'Coordinador')
        subcoordinadores = [validar_usuario(
            uid, 'Subcoordinador') for uid in subcoordinador_ids if uid]
        encuestadores = [validar_usuario(uid, 'Encuestador')
                         for uid in encuestador_ids if uid]
        choferes = [validar_usuario(uid, 'Chofer')
                    for uid in chofer_ids if uid]
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    # --- 6. Asignación atómica ---
    try:
        with transaction.atomic():
            # Guardar estado anterior para auditoría
            estado_anterior = solicitud.estado
            coordinador_anterior = solicitud.coordinador_campo
            subcoordinadores_anteriores = list(
                solicitud.subcoordinadores.all())
            encuestadores_anteriores = list(
                solicitud.relevadores_asignados.all())
            choferes_anteriores = list(solicitud.choferes.all())

            # Asignar coordinador
            solicitud.coordinador_campo = coordinador

            # Asignar subcoordinadores (ManyToMany)
            solicitud.subcoordinadores.set(subcoordinadores)

            # Asignar choferes
            solicitud.choferes.set(choferes)

            # Asignar encuestadores (usamos relevadores_asignados)
            # Además, podemos llamar al método asignar_relevadores que cambia el estado y maneja auditoría
            # Pero ese método espera una lista de usuarios y cambia el estado a 'asignado_relevadores'.
            # Como queremos cambiar el estado aquí mismo, podemos usar el método o hacerlo manual.
            # Usamos el método existente:
            solicitud.asignar_relevadores(
                encuestadores, request.user, comentario)
            # Este método actualiza: relevadores_asignados, usuario_asignado (primer relevador), estado = 'asignado_relevadores', y crea auditoría.
            # Sin embargo, también necesitamos auditar los cambios en coordinador, subcoordinadores, choferes.
            # Por eso, haremos save() adicional y auditorías manuales.

            # Guardar cambios (el método asignar_relevadores ya hace save, pero igual forzamos)
            solicitud.save()

            # --- Auditoría para coordinador ---
            valor_anterior_coord = coordinador_anterior.username if coordinador_anterior else 'Ninguno'
            valor_nuevo_coord = coordinador.username
            SolicitudRelevamientoAudit.objects.create(
                solicitud=solicitud,
                campo='coordinador_campo',
                valor_anterior=valor_anterior_coord,
                valor_nuevo=valor_nuevo_coord,
                cambiado_por=request.user,
                comentario=comentario or f"Asignación de coordinador de campo por {request.user.username}"
            )

            # --- Auditoría para subcoordinadores ---
            if subcoordinador_ids:
                ant_sub = ', '.join(
                    [u.username for u in subcoordinadores_anteriores]) or 'Ninguno'
                nue_sub = ', '.join(
                    [u.username for u in subcoordinadores]) or 'Ninguno'
                SolicitudRelevamientoAudit.objects.create(
                    solicitud=solicitud,
                    campo='subcoordinadores',
                    valor_anterior=ant_sub,
                    valor_nuevo=nue_sub,
                    cambiado_por=request.user,
                    comentario=comentario or f"Asignación de subcoordinadores por {request.user.username}"
                )

            # --- Auditoría para choferes ---
            if chofer_ids:
                ant_cho = ', '.join(
                    [u.username for u in choferes_anteriores]) or 'Ninguno'
                nue_cho = ', '.join(
                    [u.username for u in choferes]) or 'Ninguno'
                SolicitudRelevamientoAudit.objects.create(
                    solicitud=solicitud,
                    campo='choferes',
                    valor_anterior=ant_cho,
                    valor_nuevo=nue_cho,
                    cambiado_por=request.user,
                    comentario=comentario or f"Asignación de choferes por {request.user.username}"
                )

            # Nota: La auditoría de encuestadores ya la crea asignar_relevadores.

            # Mensaje de éxito
            return JsonResponse({
                'success': True,
                'message': f'Equipo de campo asignado correctamente. Coordinador: {coordinador.username}, {len(encuestadores)} encuestadores, {len(choferes)} choferes, {len(subcoordinadores)} subcoordinadores.',
                'nuevo_estado': solicitud.estado,
            })

    except Exception as e:
        return JsonResponse({'error': f'Error al asignar equipo: {str(e)}'}, status=500)


@login_required
@lider_coordinacion_required
def modificar_orden(request, orden_id):
    """
    Modifica una orden existente: fechas y equipo de campo.
    Solo permitido si la orden no está completada ni cancelada.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    orden = get_object_or_404(OrdenTrabajo, id=orden_id)
    solicitud = orden.solicitud

    # Verificar estados permitidos
    if orden.estado in ['completada', 'cancelada']:
        return JsonResponse({'error': 'No se puede modificar una orden completada o cancelada.'}, status=400)

    # Verificar que el usuario es líder del grupo asignado
    if not (solicitud.grupo_asignado and solicitud.grupo_asignado.lider == request.user):
        return JsonResponse({'error': 'No tiene permisos de líder para modificar esta orden.'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)

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
        return JsonResponse({'error': 'Las fechas son obligatorias.'}, status=400)

    from django.utils.dateparse import parse_date
    fecha_inicio_obj = parse_date(fecha_inicio)
    fecha_fin_obj = parse_date(fecha_fin)

    if not fecha_inicio_obj or not fecha_fin_obj:
        return JsonResponse({'error': 'Formato de fecha inválido.'}, status=400)

    # Validar rango de días hábiles
    hoy = timezone.now().date()
    if fecha_inicio_obj < hoy:
        return JsonResponse({'error': 'La fecha de inicio no puede ser pasada.'}, status=400)
    if fecha_inicio_obj.weekday() >= 5:
        return JsonResponse({'error': 'La fecha de inicio debe ser día hábil (L-V).'}, status=400)
    if fecha_fin_obj.weekday() >= 5:
        return JsonResponse({'error': 'La fecha de fin debe ser día hábil (L-V).'}, status=400)

    temp_form = GenerarOrdenForm()
    dias_habiles = temp_form._contar_dias_habiles(
        fecha_inicio_obj, fecha_fin_obj)
    if dias_habiles < 3 or dias_habiles > 5:
        return JsonResponse({'error': f'El período debe ser de 3 a 5 días hábiles (actual: {dias_habiles}).'}, status=400)

    # Función para validar usuarios por rol
    def validar_usuario(user_id, grupo_rol):
        if not user_id:
            return None
        usuario = get_object_or_404(User, id=user_id, is_active=True)
        # Verificar grupo relevamiento y rol específico
        if not usuario.groups.filter(name__icontains='relevamiento').exists():
            raise ValidationError(
                f'El usuario {usuario.username} no pertenece al grupo Relevamiento.')
        if not usuario.groups.filter(name__icontains=grupo_rol).exists():
            raise ValidationError(
                f'El usuario {usuario.username} no tiene el rol {grupo_rol}.')
        return usuario

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

            # Actualizar fechas de la orden
            orden.fecha_inicio_planeada = fecha_inicio_obj
            orden.fecha_fin_planeada = fecha_fin_obj
            orden.save()

            # Actualizar equipo en la solicitud
            solicitud.coordinador_campo = coordinador
            solicitud.subcoordinadores.set(subcoordinadores)
            solicitud.choferes.set(choferes)
            solicitud.relevadores_asignados.set(encuestadores)  # Encuestadores
            solicitud.save()

            # Auditoría general (puedes detallar más si quieres)
            from gerencia.models import SolicitudRelevamientoAudit
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
        return JsonResponse({'error': f'Error al modificar: {str(e)}'}, status=500)

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

    return render(request, 'inlcudes/coordinacion/coordinacion_reportes.html', context)
