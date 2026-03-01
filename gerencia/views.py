import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.db.models import Q, Prefetch
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView


from administrador.models import Grupo, TipoObjetivo
from coordinacion.models import OrdenTrabajo
from core.forms import ColoniaForm, DistritoForm
from core.models import Colonia, Departamento, Distrito
from gerencia.models import SolicitudRelevamiento, SolicitudRelevamientoAudit, Objetivo
from gerencia.forms import CrearSolicitudRelevamientoForm, EditarSolicitudRelevamientoForm, ObjetivoForm
from datetime import datetime
from django.utils import timezone


# MUESTRA LA VISTA DEL ADMINISTRADOR


class GerenciaView(LoginRequiredMixin, TemplateView):
    template_name = 'gerencia/gerente_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Para el modal de creación de roles
        context['permisos'] = Permission.objects.all()

        # Agregamos los QuerySets para que el template pueda contar
        context['departamentos'] = Departamento.objects.all()
        context['distritos'] = Distrito.objects.all()
        context['colonias'] = Colonia.objects.all()

        # Agregar objetivos activos recientes
        try:
            anio_actual = datetime.now().year
            objetivos_activos = Objetivo.objects.filter(anio=anio_actual, activo=True).select_related('grupo', 'tipo_objetivo').order_by('grupo__nombre')[:8]

            context['objetivos_activos'] = [
                {
                    'id': o.id,
                    'grupo_nombre': o.grupo.nombre,
                    'tipo_nombre': o.tipo_objetivo.nombre,
                    'meta': o.meta,
                    'avance_actual': o.avance_actual,
                    'porcentaje_avance': o.porcentaje_avance,
                    'fecha_fin': o.fecha_fin,
                }
                for o in objetivos_activos
            ]
        except Exception:
            context['objetivos_activos'] = []

        # Agregar solicitudes cuyo/ cuya Orden de Trabajo esté completada
        try:
            ordenes_qs = OrdenTrabajo.objects.select_related('solicitud__colonia', 'coordinador_responsable').filter(estado='completada', activa=True).order_by('-fecha_creacion')[:8]

            solicitudes_dashboard = []
            for orden in ordenes_qs:
                sol = orden.solicitud
                colonia = sol.colonia
                distrito = colonia.distritos.first() if colonia and hasattr(colonia, 'distritos') and colonia.distritos.exists() else None
                departamento = distrito.departamento if distrito else None

                # Conteos: encuestas asociadas a la orden y archivos (archivos subcoordinador + documentos/fotos de relevamientos)
                encuestas_total = orden.relevamientos.count()
                archivos_subcoor = orden.archivos_subcoordinador.count()
                archivos_relevamientos = 0
                for r in orden.relevamientos.all():
                    if hasattr(r, 'documentos'):
                        archivos_relevamientos += r.documentos.count()
                    if hasattr(r, 'fotos'):
                        archivos_relevamientos += r.fotos.count()

                total_archivos = archivos_subcoor + archivos_relevamientos

                solicitudes_dashboard.append({
                    'id': sol.id,
                    'colonia_nombre': colonia.nombre if colonia else 'Sin colonia',
                    'distrito_nombre': distrito.nombre if distrito else 'Sin distrito',
                    'departamento_nombre': departamento.nombre if departamento else 'Sin departamento',
                    'grupo_nombre': sol.grupo_asignado.nombre if sol.grupo_asignado else '-',
                    'fecha_cierre': orden.fecha_fin_real or sol.fecha_finalizacion,
                    'encuestas_total': encuestas_total,
                    'total_archivos': total_archivos,
                    'estado_orden': orden.get_estado_display(),
                })

            context['solicitudes_dashboard'] = solicitudes_dashboard
        except Exception:
            context['solicitudes_dashboard'] = []

        return context

# LISTA TODAS LAS SOLICITUDES (sin parámetro)


@login_required
def lista_solicitudes_relevamiento(request):
    """
    Lista todas las solicitudes de relevamiento con información de departamento y distrito
    """
    # Optimizar las consultas CON información de grupos
    solicitudes = SolicitudRelevamiento.objects.exclude(grupo_asignado__nombre='ANALISIS').select_related(
        "colonia",
        "creado_por",
        "grupo_asignado",
        "usuario_asignado",
        "asignado_por"
    ).prefetch_related(
        "colonia__distritos__departamento"
    ).all().order_by('-fecha_creacion')

    # Agregar información adicional a cada solicitud
    for solicitud in solicitudes:
        distritos = solicitud.colonia.distritos.all()
        if distritos.exists():
            distrito = distritos.first()
            solicitud.distrito = distrito
            solicitud.departamento = distrito.departamento
        else:
            solicitud.distrito = None
            solicitud.departamento = None

        # Determina si la solicitud puede ser editada
        puede_editar_estado = solicitud.estado == 'pendiente_asignacion_sig'
        tiene_permisos_editar = solicitud.puede_gestionar(
            request.user) or request.user.is_superuser

        solicitud.puede_editar = puede_editar_estado and tiene_permisos_editar

        # Determina si la solicitud puede ser eliminada
        puede_eliminar_estado = solicitud.estado == 'pendiente_asignacion_sig'
        es_superuser_o_creador = request.user.is_superuser or request.user == solicitud.creado_por

        solicitud.puede_borrar = puede_eliminar_estado and es_superuser_o_creador

    # Obtener mensaje toast de la sesión si existe
    toast_message = request.session.pop(
        'toast_message', None) if request.session else None

    # Obtener estadísticas usando los métodos del modelo
    estadisticas = SolicitudRelevamiento.obtener_estadisticas()
    estadisticas_por_estado = SolicitudRelevamiento.obtener_estadisticas_por_estado()

    # Recalcular 'finalizadas' usando órdenes de trabajo con estado 'completada'
    try:
        ordenes_finalizadas_count = OrdenTrabajo.objects.filter(estado='completada').count()
        estadisticas['finalizadas'] = ordenes_finalizadas_count
    except Exception:
        # en caso de error, mantener el valor anterior
        pass

    # Solicitudes recientes (últimas 10)
    solicitudes_recientes = SolicitudRelevamiento.obtener_solicitudes_recientes(
        10)

    return render(request, "includes/gerencia/tablas/listar_solicitud_relevamiento.html", {
        "solicitudes": solicitudes,
        "toast_message": toast_message,
        "estadisticas": estadisticas,
        "estadisticas_por_estado": estadisticas_por_estado,
        "solicitudes_recientes": solicitudes_recientes,
    })

# DETALLE DE SOLICITUD (NUEVA VISTA)


@login_required
def detalle_solicitud(request, solicitud_id):
    """Vista detallada de una solicitud"""
    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)

    # Obtener auditorías
    auditorias = solicitud.auditorias.all().select_related('cambiado_por')

    # Determinar qué grupos pueden ser asignados según el estado
    grupos_disponibles = []
    puede_asignar_grupo = False
    puede_asignar_usuario = False

    # Lógica para asignación de grupo
    if solicitud.estado in ["pendiente_asignacion_sig", "pendiente_asignacion_analista"]:
        # Determinar qué tipo de grupo necesita
        if solicitud.estado == "pendiente_asignacion_sig":
            # Buscar grupos con roles de digitalización
            grupos_disponibles = Grupo.objects.filter(
                activo=True,
                roles_asociados__nombre__icontains='digitalizador'
            ).distinct()
        else:  # pendiente_asignacion_analista
            # Buscar grupos con roles de análisis
            grupos_disponibles = Grupo.objects.filter(
                activo=True,
                roles_asociados__nombre__icontains='analista'
            ).distinct()

        # Verificar si el usuario puede asignar (líder de algún grupo disponible o superusuario)
        puede_asignar_grupo = any(
            grupo.lider == request.user for grupo in grupos_disponibles
        ) or request.user.is_superuser

    # Lógica para asignación de usuario
    elif solicitud.grupo_asignado and (request.user == solicitud.grupo_asignado.lider or request.user.is_superuser):
        puede_asignar_usuario = True

    # Usuarios disponibles para asignación (solo del grupo asignado)
    usuarios_disponibles = []
    if puede_asignar_usuario and solicitud.grupo_asignado:
        usuarios_disponibles = solicitud.grupo_asignado.usuarios.filter(
            estado='ACTIVO', is_active=True
        )

    return render(request, 'gerencia/detalle_solicitud.html', {
        'solicitud': solicitud,
        'auditorias': auditorias,
        'grupos_disponibles': grupos_disponibles,
        'usuarios_disponibles': usuarios_disponibles,
        'puede_asignar_grupo': puede_asignar_grupo,
        'puede_asignar_usuario': puede_asignar_usuario,
    })

# ASIGNAR GRUPO A SOLICITUD


@login_required
@require_POST
def asignar_grupo(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)
    grupo_id = request.POST.get('grupo_id')
    grupo = get_object_or_404(Grupo, id=grupo_id, activo=True)

    # Validar que la solicitud esté en estado pendiente de asignación
    if solicitud.estado not in ["pendiente_asignacion_sig", "pendiente_asignacion_analista"]:
        return JsonResponse({'error': 'La solicitud no está pendiente de asignación de grupo'}, status=400)
    # Verificar permisos (líder del grupo o superusuario)
    if not (request.user == grupo.lider or request.user.is_superuser):
        return JsonResponse({'error': 'No tiene permisos'}, status=403)

    solicitud.grupo_asignado = grupo
    solicitud.usuario_asignado = None
    solicitud.asignado_por = request.user
    solicitud.save()

    return JsonResponse({'success': True, 'message': f'Grupo {grupo.nombre} asignado'})


# CAMBIAR ESTADO DE SOLICITUD


@login_required
@require_POST
def cambiar_estado(request, solicitud_id):
    """Cambia el estado de la solicitud (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)
    nuevo_estado = request.POST.get('estado')
    comentario = request.POST.get('comentario', '')

    # Validar permiso para cambiar estado
    if not solicitud.puede_cambiar_estado(request.user, nuevo_estado):
        return JsonResponse({'error': 'No tiene permisos para cambiar a este estado'}, status=403)

    # Validar transición de estado
    estado_anterior = solicitud.estado

    # Verificar si el nuevo estado está permitido
    estados_permitidos = solicitud.obtener_estados_siguientes(request.user)
    if nuevo_estado not in estados_permitidos:
        return JsonResponse({'error': 'Transición de estado no permitida'}, status=400)

    solicitud.estado = nuevo_estado

    try:
        solicitud.save()
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)

    # Registrar auditoría del cambio de estado
    SolicitudRelevamientoAudit.objects.create(
        solicitud=solicitud,
        campo='estado',
        valor_anterior=estado_anterior,
        valor_nuevo=nuevo_estado,
        cambiado_por=request.user,
        comentario=comentario or f"Estado cambiado de {estado_anterior} a {nuevo_estado}"
    )

    return JsonResponse({
        'success': True,
        'message': f'Estado cambiado a {solicitud.get_estado_display()}'
    })


@login_required
def obtener_datos_solicitud(request, pk):
    """Obtener datos COMPLETOS de una solicitud para el modal de detalles (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, pk=pk)

    # Obtener información jerárquica
    colonia = solicitud.colonia
    distrito = colonia.distritos.first() if colonia.distritos.exists() else None
    departamento = distrito.departamento if distrito else None

    # Obtener información de asignación PARA EL MODAL DE DETALLES
    grupo_info_detalle = None
    if solicitud.grupo_asignado:
        grupo_info_detalle = {
            'nombre': solicitud.grupo_asignado.nombre,
            'lider': solicitud.grupo_asignado.lider.username if solicitud.grupo_asignado.lider else None,
            'color': solicitud.grupo_asignado.color or '#6c757d'
        }

    usuario_info_detalle = None
    if solicitud.usuario_asignado:
        usuario_info_detalle = {
            'username': solicitud.usuario_asignado.username,
            'email': solicitud.usuario_asignado.email,
            'nombre_completo': f"{solicitud.usuario_asignado.first_name} {solicitud.usuario_asignado.last_name}".strip() or solicitud.usuario_asignado.username
        }

    # Última asignación al digitalizador (guardada en app sig)
    usuario_digitalizador_detalle = None
    try:
        from sig.models import AsignacionDigitalizador
        ultima = AsignacionDigitalizador.objects.filter(solicitud=solicitud).select_related('usuario_asignado').order_by('-fecha_asignacion').first()
        if ultima and ultima.usuario_asignado:
            fecha_asig = timezone.localtime(ultima.fecha_asignacion) if ultima.fecha_asignacion else None
            usuario_digitalizador_detalle = {
                'id': ultima.usuario_asignado.id,
                'username': ultima.usuario_asignado.username,
                'nombre_completo': f"{ultima.usuario_asignado.first_name} {ultima.usuario_asignado.last_name}".strip() or ultima.usuario_asignado.username,
                'fecha_asignacion': fecha_asig.strftime("%d/%m/%Y %H:%M") if fecha_asig else None
            }
    except Exception:
        usuario_digitalizador_detalle = None

    # Obtener auditorías recientes (últimas 3)
    auditorias_recientes = solicitud.auditorias.all(
    ).select_related('cambiado_por')[:3]
    auditorias_data = []
    for auditoria in auditorias_recientes:
        fecha_a = timezone.localtime(auditoria.fecha) if auditoria.fecha else None
        auditorias_data.append({
            'fecha': fecha_a.strftime("%d/%m/%Y %H:%M") if fecha_a else None,
            'cambiado_por': auditoria.cambiado_por.username if auditoria.cambiado_por else 'Sistema',
            'comentario': auditoria.comentario[:100] + '...' if auditoria.comentario and len(auditoria.comentario) > 100 else auditoria.comentario
        })

    data = {
        'success': True,
        'solicitud': {
            'id': solicitud.id,
            'tipo': solicitud.tipo,
            'tipo_display': solicitud.get_tipo_display(),
            'prioridad': solicitud.prioridad,
            'prioridad_display': solicitud.get_prioridad_display(),
            'estado': solicitud.estado,
            'estado_display': solicitud.get_estado_display(),
            'observaciones': solicitud.observaciones,
            'fecha_creacion': timezone.localtime(solicitud.fecha_creacion).strftime("%d/%m/%Y %H:%M") if solicitud.fecha_creacion else None,
            'fecha_modificacion': timezone.localtime(solicitud.fecha_modificacion).strftime("%d/%m/%Y %H:%M") if solicitud.fecha_modificacion else None,
            'creado_por': solicitud.creado_por.username if solicitud.creado_por else 'Desconocido',
            'motivo_rechazo': solicitud.motivo_rechazo,
        },
        'colonia': {
            'nombre': colonia.nombre,
            'codigo': colonia.codigo,
            'tiene_relevamiento': colonia.tiene_relevamiento,
        },
        'distrito': {
            'nombre': distrito.nombre if distrito else "Sin distrito",
            'codigo': distrito.codigo if distrito else "",
        },
        'departamento': {
            'nombre': departamento.nombre if departamento else "Sin departamento",
            'codigo': departamento.codigo if departamento else "",
        },
        # Datos básicos para modal de EDICIÓN
        'estado': solicitud.estado,
        'estado_display': solicitud.get_estado_display(),
        'tipo': solicitud.tipo,
        'tipo_display': solicitud.get_tipo_display(),
        'observaciones': solicitud.observaciones,
        'prioridad': solicitud.prioridad,
        'grupo_asignado_id': solicitud.grupo_asignado.id if solicitud.grupo_asignado else None,
        'usuario_asignado_id': solicitud.usuario_asignado.id if solicitud.usuario_asignado else None,
        'motivo_rechazo': solicitud.motivo_rechazo,
        'tiene_usuario_asignado': solicitud.usuario_asignado is not None,
        'puede_editar': solicitud.puede_gestionar(request.user) or request.user.is_superuser,

        # Datos ampliados para modal de DETALLES (nombres diferentes)
        'auditorias_recientes': auditorias_data,
        'grupo_info': grupo_info_detalle,
        'usuario_info': usuario_info_detalle,
        'usuario_digitalizador': usuario_digitalizador_detalle,
    }

    return JsonResponse(data)


@login_required
def crear_solicitud_relevamiento(request, colonia_id):
    colonia = get_object_or_404(Colonia, pk=colonia_id)

    if request.method == "POST":

        # Verificar si ya existe solicitud activa ANTES de crear el formulario
        solicitudes_activas = SolicitudRelevamiento.objects.filter(
            colonia=colonia,
            estado__in=[estado for estado, _ in SolicitudRelevamiento.ESTADOS
                        if not getattr(SolicitudRelevamiento, 'relevamiento_terminado', False)
                          and not getattr(SolicitudRelevamiento, 'actualizacion_terminado', False)
                            or estado not in ["rechazado", "finalizado"]]
        )

        if solicitudes_activas.exists():
            return JsonResponse({
                "success": False,
                "errors": {"__all__": [f"Ya existe una solicitud activa para la colonia {colonia.nombre}"]},
                "message": "No se puede crear la solicitud"
            }, status=400)

        # Crear formulario con colonia en contexto
        form = CrearSolicitudRelevamientoForm(request.POST, colonia=colonia)

        if form.is_valid():
            try:
                # OBTENER la instancia del formulario pero NO guardar aún
                solicitud = form.save(commit=False)

                # Asignar manualmente los campos
                solicitud.colonia = colonia
                solicitud.creado_por = request.user

                # Marcar que se creará auditoría manual (para evitar duplicación en signals)
                solicitud._auditoria_creada = True
                solicitud._cambiado_por = request.user

                # Determinar automáticamente el tipo basado en si existe relevamiento previo
                if colonia.tiene_relevamiento:
                    solicitud.tipo = 'actualizacion'
                    # Para actualizaciones, va directamente a analista
                    solicitud.estado = 'pendiente_asignacion_analista'
                    # Para actualizaciones, no asignar grupo SIG
                    solicitud.grupo_asignado = None
                else:
                    solicitud.tipo = 'relevamiento'
                    # Para relevamientos nuevos, va a SIG
                    solicitud.estado = 'pendiente_asignacion_sig'
                    # Asignar automáticamente grupo SIG si está configurado
                    # (esto depende de tu lógica de negocio)
                    if not solicitud.grupo_asignado:
                        # Aquí puedes agregar lógica para asignar grupo por defecto
                        # Por ejemplo, el primer grupo SIG activo
                        grupo_sig = Grupo.objects.filter(
                            nombre__icontains='SIG',
                            activo=True
                        ).first()
                        if grupo_sig:
                            solicitud.grupo_asignado = grupo_sig

                # Si no se especifica prioridad, establecer baja por defecto
                if not solicitud.prioridad:
                    solicitud.prioridad = 'baja'

                if solicitud.estado == 'pendiente_asignacion_sig':
                    solicitud.usuario_asignado = None
                    # El campo `usuario_digitalizador` ahora se registra en la app `sig` (AsignacionDigitalizador)

                # GUARDAR ahora sí
                solicitud.save()

                # Crear auditoría de creación
                SolicitudRelevamientoAudit.objects.create(
                    solicitud=solicitud,
                    campo='creacion',
                    valor_anterior='',
                    valor_nuevo=f"Solicitud creada con prioridad {solicitud.get_prioridad_display()}",
                    cambiado_por=request.user,
                    comentario=f"Solicitud de {solicitud.get_tipo_display()} creada para {colonia.nombre}"
                )

                # También crear auditoría para estado inicial
                SolicitudRelevamientoAudit.objects.create(
                    solicitud=solicitud,
                    campo='estado',
                    valor_anterior='',
                    valor_nuevo=solicitud.estado,
                    cambiado_por=request.user,
                    comentario=f"Solicitud creada. Tipo: {solicitud.get_tipo_display()}"
                )

                # Si se asignó grupo, crear auditoría para eso también
                if solicitud.grupo_asignado:
                    SolicitudRelevamientoAudit.objects.create(
                        solicitud=solicitud,
                        campo='grupo_asignado',
                        valor_anterior='',
                        valor_nuevo=str(solicitud.grupo_asignado),
                        cambiado_por=request.user,
                        comentario=f"Asignado automáticamente al grupo {solicitud.grupo_asignado.nombre}"
                    )

                # Guardar mensaje para toast en sesión
                request.session['toast_message'] = {
                    'text': f'Solicitud para {colonia.nombre} creada exitosamente.',
                    'type': 'success'
                }

                return JsonResponse({
                    "success": True,
                    "message": "Solicitud creada exitosamente",
                    "solicitud_id": solicitud.id,
                    "redirect_url": reverse("gerencia:lista_solicitudes_relevamiento")
                })

            except Exception as e:
                print(f"ERROR al crear solicitud: {str(e)}")
                import traceback
                traceback.print_exc()

                return JsonResponse({
                    "success": False,
                    "errors": {},
                    "message": f"Error al crear la solicitud: {str(e)}"
                }, status=500)
        else:
            print(f"Errores del formulario: {form.errors}")
            return JsonResponse({
                "success": False,
                "errors": form.errors,
                "message": "Por favor corrija los errores en el formulario"
            })

    return JsonResponse({
        "success": False,
        "message": "Método no permitido"
    }, status=405)


@login_required
def editar_solicitud_relevamiento(request, pk):
    """Editar solicitud (AJAX) - AHORA INCLUYE PRIORIDAD"""
    solicitud = get_object_or_404(SolicitudRelevamiento, pk=pk)

    # NUEVO: Validar que esté en estado permitido
    if solicitud.estado != 'pendiente_asignacion_sig':
        return JsonResponse({
            'success': False,
            'message': 'Solo se pueden editar solicitudes en estado "Pendiente de asignación SIG"'
        }, status=403)

    if not solicitud.puede_gestionar(request.user):
        return JsonResponse({
            'success': False,
            'message': 'No tiene permisos para editar esta solicitud'
        }, status=403)

    if request.method == "POST":
        # Guardar valores anteriores para auditoría
        prioridad_anterior = solicitud.prioridad
        observaciones_anterior = solicitud.observaciones

        # Usar el formulario de EDICIÓN (ahora incluye prioridad)
        form = EditarSolicitudRelevamientoForm(
            request.POST, instance=solicitud)

        if form.is_valid():
            form.save()

            # Crear auditorías para cambios
            if prioridad_anterior != solicitud.prioridad:
                SolicitudRelevamientoAudit.objects.create(
                    solicitud=solicitud,
                    campo='prioridad',
                    valor_anterior=prioridad_anterior,
                    valor_nuevo=solicitud.prioridad,
                    cambiado_por=request.user,
                    comentario=f"Prioridad cambiada de {prioridad_anterior} a {solicitud.prioridad}"
                )

            if observaciones_anterior != solicitud.observaciones:
                SolicitudRelevamientoAudit.objects.create(
                    solicitud=solicitud,
                    campo='observaciones',
                    valor_anterior=observaciones_anterior[:100] + '...' if len(
                        observaciones_anterior) > 100 else observaciones_anterior,
                    valor_nuevo=solicitud.observaciones[:100] + '...' if len(
                        solicitud.observaciones) > 100 else solicitud.observaciones,
                    cambiado_por=request.user,
                    comentario="Observaciones actualizadas"
                )

            # Guardar mensaje para toast en sesión
            request.session['toast_message'] = {
                'text': f'Solicitud de {solicitud.colonia.nombre} actualizada.',
                'type': 'info'
            }

            return JsonResponse({
                'success': True,
                'message': 'Solicitud actualizada exitosamente',
                'redirect_url': reverse("gerencia:lista_solicitudes_relevamiento")
            })
        else:
            # Agregar logging para ver qué errores hay
            print(f"Errores del formulario: {form.errors}")
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'message': 'Por favor corrija los errores en el formulario'
            })

    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    }, status=405)


@login_required
def eliminar_solicitud_relevamiento(request, pk):
    """Eliminar solicitud (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, pk=pk)

    # Validar que esté en estado permitido
    if solicitud.estado != 'pendiente_asignacion_sig':
        return JsonResponse({
            'success': False,
            'message': 'Solo se pueden eliminar solicitudes en estado "Pendiente de asignación SIG"'
        }, status=403)

    if not (request.user.is_superuser or request.user == solicitud.creado_por):
        return JsonResponse({
            'success': False,
            'message': 'No tiene permisos para eliminar esta solicitud'
        }, status=403)

    if request.method == "POST":
        try:
            solicitud_id = solicitud.id
            solicitud_colonia = solicitud.colonia.nombre
            solicitud.delete()

            # Guardar mensaje para toast en sesión
            request.session['toast_message'] = {
                'text': f'La solicitud de Relevamiento: {solicitud_colonia} fue eliminada.',
                'type': 'info'
            }

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al eliminar: {str(e)}'
            }, status=500)

    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    }, status=405)


@login_required
def api_info_colonia(request, colonia_id):
    """API para obtener información de una colonia (AJAX)"""
    colonia = get_object_or_404(Colonia, pk=colonia_id)

    data = {
        'id': colonia.id,
        'nombre': colonia.nombre,
        'codigo': colonia.codigo,
        'tiene_relevamiento': colonia.tiene_relevamiento if hasattr(colonia, 'tiene_relevamiento') else False,
        'estado': colonia.estado,
        'distritos': [{
            'id': d.id,
            'nombre': d.nombre,
            'departamento': d.departamento.nombre
        } for d in colonia.distritos.all()[:3]]  # Primeros 3 distritos

    }

    return JsonResponse(data)


# ==================== VISTAS PARA OBJETIVOS ====================

@login_required
def lista_objetivos(request):
    """Vista principal de objetivos con dashboard"""
    anio_actual = datetime.now().year
    anio_seleccionado = request.GET.get('anio', anio_actual)
    
    try:
        anio_seleccionado = int(anio_seleccionado)
    except (ValueError, TypeError):
        anio_seleccionado = anio_actual
    
    # Obtener todos los objetivos activos del año
    objetivos = Objetivo.objects.filter(anio=anio_seleccionado, activo=True).select_related('creado_por', 'grupo', 'tipo_objetivo')
    # Obtener objetivos inactivos del mismo año para la tabla separada
    objetivos_inactivos = Objetivo.objects.filter(anio=anio_seleccionado, activo=False).select_related('creado_por', 'grupo', 'tipo_objetivo')
    
    # Obtener resumen agrupado
    resumen = Objetivo.obtener_resumen_por_grupo(anio_seleccionado)
    
    # Obtener años disponibles para el selector
    anios_disponibles = Objetivo.objects.values_list('anio', flat=True).distinct().order_by('-anio')
    if not anios_disponibles:
        anios_disponibles = [anio_actual]
    
    # Obtener grupos activos para el formulario
    grupos_disponibles = Grupo.objects.filter(activo=True).order_by('nombre')
    # Prefetch tipos de objetivo activos por grupo y construir lista de grupos que tengan tipos
    tipos_qs = TipoObjetivo.objects.filter(activo=True).order_by('nombre')
    grupos_prefetch = grupos_disponibles.prefetch_related(
        Prefetch('tipos_objetivo_list', queryset=tipos_qs, to_attr='tipos_activos')
    )
    grupos_con_tipos = [g for g in grupos_prefetch if getattr(g, 'tipos_activos', [])]
    # Serializar información mínima de grupos para uso en JS (modal rápido)
    grupos_serializados = []
    for g in grupos_disponibles:
        lider = getattr(g, 'lider', None)
        grupos_serializados.append({
            'id': g.id,
            'nombre': g.nombre,
            'usuarios_count': g.usuarios.count() if hasattr(g, 'usuarios') else 0,
            'lider_fullname': lider.get_full_name() if lider else None,
            'lider_username': lider.username if lider else None,
        })
    grupos_disponibles_json = json.dumps(grupos_serializados, ensure_ascii=False)
    
    # Obtener todos los tipos de objetivo activos
    tipos_objetivo_disponibles = TipoObjetivo.objects.filter(activo=True).select_related('grupo').order_by('grupo__nombre', 'nombre')
    
    context = {
        'objetivos': objetivos,
        'objetivos_inactivos': objetivos_inactivos,
        'resumen': resumen,
        'anio_seleccionado': anio_seleccionado,
        'anios_disponibles': anios_disponibles,
        'anio_actual': anio_actual,
        'grupos_disponibles': grupos_disponibles,
        'grupos_con_tipos': grupos_con_tipos,
        'tipos_objetivo_disponibles': tipos_objetivo_disponibles,
        'grupos_disponibles_json': grupos_disponibles_json,
    }
    
    return render(request, 'includes/gerencia/objetivos/gerencia_objetivos.html', context)


@login_required
def tipos_objetivo_por_grupo(request, grupo_id):
    """Obtener tipos de objetivo filtrados por grupo (AJAX)"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Solicitando tipos de objetivo para grupo {grupo_id}")
    
    try:
        # Verificar que el grupo existe
        grupo = Grupo.objects.get(id=grupo_id, activo=True)
        logger.info(f"Grupo encontrado: {grupo.nombre}")
        
        tipos_objetivo = TipoObjetivo.objects.filter(
            grupo_id=grupo_id, 
            activo=True
        ).values('id', 'nombre', 'descripcion').order_by('nombre')
        
        tipos_list = list(tipos_objetivo)
        logger.info(f"Tipos encontrados: {len(tipos_list)}")
        
        return JsonResponse({
            'success': True,
            'tipos_objetivo': tipos_list,
            'grupo_nombre': grupo.nombre
        })
    except Grupo.DoesNotExist:
        logger.error(f"Grupo {grupo_id} no encontrado")
        return JsonResponse({
            'success': False,
            'message': 'Grupo no encontrado'
        }, status=404)
    except Exception as e:
        logger.error(f"Error al cargar tipos: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
@require_POST
def crear_objetivo(request):
    """Crear un nuevo objetivo"""
    grupo_id = request.POST.get('grupo_id')
    
    if not grupo_id:
        return JsonResponse({
            'success': False,
            'message': 'No se especificó el grupo para el objetivo'
        }, status=400)
    
    try:
        grupo = Grupo.objects.get(id=grupo_id, activo=True)
    except Grupo.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'El grupo seleccionado no existe o no está activo'
        }, status=404)
    
    # Soportar campo 'observacion' en los templates: mapear a 'descripcion' que usa el modelo/form
    post_data = request.POST.copy()
    if 'observacion' in post_data and 'descripcion' not in post_data:
        post_data['descripcion'] = post_data.get('observacion', '')

    form = ObjetivoForm(post_data, grupo=grupo)
    
    if form.is_valid():
        objetivo = form.save(commit=False)
        objetivo.creado_por = request.user
        objetivo.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Objetivo creado exitosamente',
            'objetivo_id': objetivo.id
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Error al crear el objetivo',
            'errors': form.errors
        }, status=400)


@login_required
def obtener_objetivo(request, pk):
    """Obtener datos de un objetivo para edición (AJAX)"""
    objetivo = get_object_or_404(Objetivo, pk=pk)
    
    data = {
        'id': objetivo.id,
        'grupo_id': objetivo.grupo.id,
        'grupo_nombre': objetivo.grupo.nombre,
        'tipo_objetivo_id': objetivo.tipo_objetivo.id,
        'tipo_objetivo_nombre': objetivo.tipo_objetivo.nombre,
        'fecha_fin': objetivo.fecha_fin.strftime('%Y-%m-%d'),
        'anio': objetivo.anio,
        'meta': objetivo.meta,
        'avance_actual': objetivo.avance_actual,
        'observacion': objetivo.descripcion or '',
        'activo': objetivo.activo,
        'porcentaje_avance': objetivo.porcentaje_avance,
        'estado_semaforo': objetivo.estado_semaforo,
        'categoria': Objetivo.get_categoria_grupo(objetivo.grupo),
    }
    
    return JsonResponse(data)


@login_required
@require_POST
def editar_objetivo(request, pk):
    """Editar un objetivo existente"""
    objetivo = get_object_or_404(Objetivo, pk=pk)
    # Soporte para toggle de activo desde el modal (botón activar/desactivar)
    if request.POST.get('toggle_activo'):
        objetivo.activo = not objetivo.activo
        objetivo.save()
        return JsonResponse({
            'success': True,
            'message': 'Objetivo actualizado exitosamente',
            'objetivo_id': objetivo.id,
            'activo': objetivo.activo
        })

    # Pasar el grupo del objetivo existente al formulario
    post_data = request.POST.copy()
    if 'observacion' in post_data and 'descripcion' not in post_data:
        post_data['descripcion'] = post_data.get('observacion', '')

    form = ObjetivoForm(post_data, instance=objetivo, grupo=objetivo.grupo)

    if form.is_valid():
        form.save()

        return JsonResponse({
            'success': True,
            'message': 'Objetivo actualizado exitosamente',
            'objetivo_id': objetivo.id,
            'porcentaje_avance': objetivo.porcentaje_avance
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Error al actualizar el objetivo',
            'errors': form.errors
        }, status=400)


@login_required
@require_POST
def eliminar_objetivo(request, pk):
    """Eliminar permanentemente un objetivo (DELETE)"""
    objetivo = get_object_or_404(Objetivo, pk=pk)
    try:
        objetivo.delete()
        return JsonResponse({
            'success': True,
            'message': 'Objetivo eliminado exitosamente'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al eliminar objetivo: {str(e)}'
        }, status=500)


@login_required
@require_POST
def actualizar_avance_objetivo(request, pk):
    """Actualizar solo el avance de un objetivo (AJAX)"""
    objetivo = get_object_or_404(Objetivo, pk=pk)
    
    try:
        data = json.loads(request.body)
        nuevo_avance = data.get('avance_actual')
        
        if nuevo_avance is None:
            return JsonResponse({
                'success': False,
                'message': 'Debe proporcionar un valor de avance'
            }, status=400)
        
        nuevo_avance = int(nuevo_avance)
        
        if nuevo_avance < 0:
            return JsonResponse({
                'success': False,
                'message': 'El avance no puede ser negativo'
            }, status=400)
        
        objetivo.avance_actual = nuevo_avance
        objetivo.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Avance actualizado exitosamente',
            'avance_actual': objetivo.avance_actual,
            'porcentaje_avance': objetivo.porcentaje_avance,
            'estado_semaforo': objetivo.estado_semaforo
        })
        
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({
            'success': False,
            'message': 'Datos inválidos'
        }, status=400)
