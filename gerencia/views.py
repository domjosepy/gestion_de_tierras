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

from administrador.models import Grupo, Rol
from core.forms import ColoniaForm, DistritoForm
from core.models import Colonia, Departamento, Distrito
from gerencia.forms import EditarSolicitudRelevamientoForm, SolicitudRelevamientoForm, CrearSolicitudRelevamientoForm
from gerencia.models import SolicitudRelevamiento, SolicitudRelevamientoAudit

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

        # Propiedades para el template
        solicitud.puede_editar = solicitud.puede_gestionar(
            request.user) or request.user.is_superuser
        solicitud.puede_borrar = request.user.is_superuser or request.user == solicitud.creado_por

    # Obtener mensaje toast de la sesión si existe
    toast_message = request.session.pop(
        'toast_message', None) if request.session else None

    # Obtener estadísticas usando los métodos del modelo
    estadisticas = SolicitudRelevamiento.obtener_estadisticas()
    estadisticas_por_estado = SolicitudRelevamiento.obtener_estadisticas_por_estado()

    # Solicitudes recientes (últimas 5)
    solicitudes_recientes = SolicitudRelevamiento.obtener_solicitudes_recientes(
        5)

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

# ASIGNAR USUARIO A SOLICITUD


@login_required
@require_POST
def asignar_usuario(request, solicitud_id):
    """Asigna un usuario a la solicitud (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)
    usuario_id = request.POST.get('usuario_id')

    # Validar que haya grupo asignado
    if not solicitud.grupo_asignado:
        return JsonResponse({'error': 'No hay grupo asignado'}, status=400)

    # Verificar permisos (líder del grupo asignado o superusuario)
    if not (request.user == solicitud.grupo_asignado.lider or request.user.is_superuser):
        return JsonResponse({'error': 'No tiene permisos para asignar usuarios'}, status=403)

    # Obtener usuario
    usuario = get_object_or_404(
        User, id=usuario_id, estado='ACTIVO', is_active=True)

    # Verificar que el usuario pertenece al grupo
    if usuario not in solicitud.grupo_asignado.usuarios.all():
        return JsonResponse({'error': 'El usuario no pertenece al grupo asignado'}, status=400)

    # Asignar usuario
    solicitud.usuario_asignado = usuario
    solicitud.asignado_por = request.user
    solicitud.save()

    # Crear auditoría
    SolicitudRelevamientoAudit.objects.create(
        solicitud=solicitud,
        previo="Sin usuario asignado",
        nuevo=f"Usuario: {usuario.username}",
        cambiado_por=request.user,
        comentario=f"Asignado a {usuario.username}"
    )

    return JsonResponse({
        'success': True,
        'message': f'Usuario {usuario.username} asignado correctamente'
    })

# CAMBIAR ESTADO DE SOLICITUD


@login_required
@require_POST
def cambiar_estado(request, solicitud_id):
    """Cambia el estado de la solicitud (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, id=solicitud_id)
    nuevo_estado = request.POST.get('estado')
    comentario = request.POST.get('comentario', '')

    # Validar permiso para cambiar estado
    if not solicitud.puede_gestionar(request.user):
        return JsonResponse({'error': 'No tiene permisos para cambiar el estado'}, status=403)

    # Validar transición de estado
    estado_anterior = solicitud.estado
    solicitud.estado = nuevo_estado

    try:
        solicitud.save()
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)

    # Crear auditoría
    SolicitudRelevamientoAudit.objects.create(
        solicitud=solicitud,
        previo=estado_anterior,
        nuevo=nuevo_estado,
        cambiado_por=request.user,
        comentario=comentario
    )

    return JsonResponse({
        'success': True,
        'message': f'Estado cambiado a {solicitud.get_estado_display()}'
    })

# LAS VISTAS EXISTENTES (MANTENIENDO COMPATIBILIDAD)


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
        'grupo_asignado_id': solicitud.grupo_asignado.id if solicitud.grupo_asignado else None,  # CAMBIADO
        'usuario_asignado_id': solicitud.usuario_asignado.id if solicitud.usuario_asignado else None,  # CAMBIADO
        'motivo_rechazo': solicitud.motivo_rechazo,
        'tiene_usuario_asignado': solicitud.usuario_asignado is not None,
        'puede_editar': solicitud.puede_gestionar(request.user) or request.user.is_superuser,

        # Datos ampliados para modal de DETALLES (nombres diferentes)
        'auditorias_recientes': auditorias_data,
        'grupo_info': grupo_info_detalle,  # CAMBIADO
        'usuario_info': usuario_info_detalle,  # CAMBIADO
    }

    return JsonResponse(data)


@login_required
def crear_solicitud_relevamiento(request, colonia_id):
    colonia = get_object_or_404(Colonia, pk=colonia_id)

    print(f"=== DEBUG: Creando solicitud para colonia ID: {colonia_id} ===")
    print(f"Colonia: {colonia.nombre}")

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

                # Determinar automáticamente el tipo basado en si existe relevamiento previo
                if colonia.tiene_relevamiento:
                    solicitud.tipo = 'actualizacion'
                else:
                    solicitud.tipo = 'relevamiento'

                # Estado inicial
                solicitud.estado = 'pendiente_asignacion_sig'

                # GUARDAR ahora sí
                solicitud.save()

                print(f"Solicitud creada exitosamente: ID {solicitud.id}")

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
    """Editar solicitud (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, pk=pk)

    if not solicitud.puede_gestionar(request.user):
        return JsonResponse({
            'success': False,
            'message': 'No tiene permisos para editar esta solicitud'
        }, status=403)  # 403 Forbidden que no tiene permisos

    if request.method == "POST":
        # Usar el formulario de EDICIÓN (solo observaciones)
        form = EditarSolicitudRelevamientoForm(
            request.POST, instance=solicitud)
        if form.is_valid():
            form.save()

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
    }, status=405)  # 405 Method Not Allowed que no está permitido el método


@login_required
def eliminar_solicitud_relevamiento(request, pk):
    """Eliminar solicitud (AJAX)"""
    solicitud = get_object_or_404(SolicitudRelevamiento, pk=pk)

    if not (request.user.is_superuser or request.user == solicitud.creado_por):
        return JsonResponse({
            'success': False,
            'message': 'No tiene permisos para eliminar esta solicitud'
        }, status=403)  # 403 Forbidden que no tiene permisos: solo superusuario o creador

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
            }, status=500)  # 500 Internal Server Error en caso de error

    return JsonResponse({
        'success': False,
        'message': 'Método no permitido'
    }, status=405)  # 405 Method Not Allowed que no está permitido el método


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
