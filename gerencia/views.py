import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from administrador.models import Grupo
from core.forms import ColoniaForm, DistritoForm
from core.models import Colonia, Departamento, Distrito
from gerencia.models import SolicitudRelevamiento, SolicitudRelevamientoAudit
from gerencia.forms import CrearSolicitudRelevamientoForm, EditarSolicitudRelevamientoForm


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

        return context

# LISTA TODAS LAS SOLICITUDES (sin parámetro)


@login_required
def lista_solicitudes_relevamiento(request):
    """
    Lista todas las solicitudes de relevamiento con información de departamento y distrito
    """
    # Optimizar las consultas CON información de grupos
    solicitudes = SolicitudRelevamiento.objects.select_related(
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

    # Obtener auditorías recientes (últimas 3)
    auditorias_recientes = solicitud.auditorias.all(
    ).select_related('cambiado_por')[:3]
    auditorias_data = []
    for auditoria in auditorias_recientes:
        auditorias_data.append({
            'fecha': auditoria.fecha.strftime("%d/%m/%Y %H:%M"),
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
            'fecha_creacion': solicitud.fecha_creacion.strftime("%d/%m/%Y %H:%M"),
            'fecha_modificacion': solicitud.fecha_modificacion.strftime("%d/%m/%Y %H:%M"),
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
    }

    return JsonResponse(data)


@login_required
def crear_solicitud_relevamiento(request, colonia_id):
    colonia = get_object_or_404(Colonia, pk=colonia_id)

    if request.method == "POST":
        print(f"Datos POST recibidos: {dict(request.POST)}")

        # Verificar si ya existe solicitud activa ANTES de crear el formulario
        solicitudes_activas = SolicitudRelevamiento.objects.filter(
            colonia=colonia,
            estado__in=[estado for estado, _ in SolicitudRelevamiento.ESTADOS
                        if estado not in ["rechazado", "finalizado"]]
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
                    solicitud.usuario_digitalizador = None

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
