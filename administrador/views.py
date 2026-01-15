# Standard library imports
import json

# Django core imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Permission
from django.contrib.auth.views import LoginView as DjangoLoginView, PasswordChangeView
from django.db.models import Q, Count
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.core import serializers
from django.shortcuts import render, get_list_or_404, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy, NoReverseMatch
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, CreateView, ListView
from core.notificaciones.utils import notificar_a_admins
from administrador.models import Grupo

# Local application imports
from .forms import (CustomUserCreationForm, CustomPasswordChangeForm,
                    SimpleUserCreationForm, RolForm, AsignacionPermisosForm, GrupoForm)
from .models import User, Rol

# VISTA DE INICIO DE SESION PERSONALIZADA


class LoginView(DjangoLoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

    def form_invalid(self, form):
        messages.error(self.request, "Usuario o contraseña incorrectos.")
        return super().form_invalid(form)

    def form_valid(self, form):
        messages.success(
            self.request, f"¡Bienvenido, {form.get_user().username}!")
        return super().form_valid(form)

    def get_success_url(self):
        user = self.request.user

        # Normalizamos el rol
        rol_slug = user.rol_nombre.lower().replace(" ", "-")
        nombre_url = f"{rol_slug}_dashboard"

        # --- MAPEO de roles a namespaces reales ---
        namespace_por_rol = {
            "gerente": "gerencia",
            "sig": "sig",
            "digitalizador": "digitalizador",
            "administrador": "administrador",
            "invitado": "invitado",
            "analista": "analista",
            "tecnico": "tecnico",
            "supervisor": "supervisor",
            "coordinador": "coordinador",

            # por ejemplo, si tenés un rol llamado "ventas"
            # podés agregar más roles aquí
        }

        namespace = namespace_por_rol.get(rol_slug, None)

        # Primero intentamos con namespace si existe
        if namespace:
            try:
                return reverse_lazy(f"{namespace}:{nombre_url}")
            except NoReverseMatch:
                pass

        # Si falla, intentamos sin namespace
        # Intentar con namespace por defecto
        try:
            return reverse_lazy(f"administrador:{nombre_url}")
        except NoReverseMatch:
            pass

        # Intentar sin namespace (por si existe)
        try:
            return reverse_lazy(nombre_url)
        except NoReverseMatch:
            return reverse_lazy("administrador:home")


# MUESTRA LA VISTA DEL HOME

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'
# MUESTRA LA VISTA DEL INVITADO


class InvitadoView(LoginRequiredMixin, TemplateView):
    template_name = 'invitado_dashboard.html'

# MUESTRA LA VISTA DEL ADMINISTRADOR


class AdminView(LoginRequiredMixin, TemplateView):
    template_name = 'administrador/administrador_dashboard.html'

    def get_context_data(self, **kwargs):
        # Llama al método padre para obtener el contexto base
        context = super().get_context_data(**kwargs)
        # Para el modal de creación de roles
        context['permisos'] = Permission.objects.all()

        # Estadísticas
        context['total_usuarios'] = User.objects.count()
        context['ultima_actividad'] = User.objects.order_by(
            '-last_login').first().last_login if User.objects.exists() else None
        context['roles'] = Rol.objects.all()

        # Querysets para las pestañas
        context['usuarios_todos'] = User.objects.all().order_by('-date_joined')
        context['usuarios_pendientes'] = User.objects.filter(
            estado='PENDIENTE').order_by('-date_joined')
        context['usuarios_activos'] = User.objects.filter(
            estado='ACTIVO').order_by('-date_joined')
        context['usuarios_inactivos'] = User.objects.filter(
            estado='INACTIVO').order_by('-date_joined')

        # Columnas para la tabla reutilizable
        context['columnas'] = [
            {'nombre': 'Usuario', 'campo': 'username'},
            {'nombre': 'Nombre', 'campo': 'first_name'},
            {'nombre': 'Apellido', 'campo': 'last_name'},
            {'nombre': 'Email', 'campo': 'email'},
            {'nombre': 'Rol', 'campo': 'rol_nombre'},
            {'nombre': 'Estado', 'campo': 'estado'},
            {'nombre': 'Creado por', 'campo': 'creado_por'},
            {'nombre': 'Último login', 'campo': 'last_login'},
        ]

        # Evolución de usuarios por mes (últimos 12 meses)
        evolucion = (
            User.objects.annotate(mes=TruncMonth('date_joined'))
            .values('mes')
            .annotate(cantidad=Count('id'))
            .order_by('mes')
        )
        evolucion_fechas = [e['mes'].strftime('%b %Y') for e in evolucion]
        evolucion_cantidades = [e['cantidad'] for e in evolucion]
        context['evolucion_fechas'] = json.dumps(evolucion_fechas)
        context['evolucion_cantidades'] = json.dumps(evolucion_cantidades)

        # Distribución de roles
        roles = Rol.objects.all()
        roles_labels = [rol.nombre for rol in roles]
        roles_cantidades = [User.objects.filter(
            rol=rol).count() for rol in roles]
        context['roles_labels'] = json.dumps(roles_labels)
        context['roles_cantidades'] = json.dumps(roles_cantidades)

        return context


# ==================================================================
# VISTA DE REGISTRO PERSONALIZADA -- CREACION PERSONAL DE USUARIO
# ==================================================================

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("administrador:login")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "¡Registro exitoso! Por favor inicia sesión."
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            "Error en el registro. Por favor corrige los errores.",
            extra_tags='danger'
        )
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hide_sidebar'] = True   # Para ocultar barra lateral
        context['hide_notifications'] = True  # Para ocultar notificaciones
        return context

# VISTA PERSONALIZADA PARA CAMBIO DE CONTRASEÑA


class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'registration/password_change_form.html'

    def get_success_url(self):
        # Obtiene el rol del usuario actual
        user = self.request.user
        rol_slug = user.rol_nombre.lower().replace(" ", "-")

        # Construye el nombre de la URL del dashboard correspondiente
        nombre_url = f"{rol_slug}_dashboard"

        try:
            return reverse_lazy(nombre_url)
        except Exception:
            return reverse_lazy('administrador:home')

    def form_valid(self, form):
        messages.success(
            self.request,
            "¡Tu contraseña ha sido cambiada exitosamente!"
        )
        return super().form_valid(form)

# ======================================
# Vistas para Grupos
# ======================================


@login_required
def listar_grupos(request):
    """Lista todos los grupos con usuarios y roles pre-cargados"""
    grupos = Grupo.objects.prefetch_related(
        'usuarios', 'roles_asociados').all()
    usuarios = User.objects.filter(estado='ACTIVO')
    roles = Rol.objects.all()

    return render(request, 'includes/administrador/tablas/listar_grupos.html', {
        'grupos': grupos,
        'usuarios': usuarios,
        'roles': roles,
        'title': 'Gestión de Grupos'
    })


@require_POST
@login_required
def crear_grupo(request):
    """Crea un nuevo grupo con validaciones AJAX"""
    form = GrupoForm(request.POST, request=request)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if form.is_valid():
        grupo = form.save()

        # Notificar a administradores
        notificar_a_admins(
            mensaje=f'Se ha creado un nuevo grupo: "{grupo.nombre}".',
            tipo="INFO",
            exclude_user=request.user,
            link=reverse("administrador:listar_grupos")
        )

        messages.success(
            request, f'Grupo "{grupo.nombre}" creado exitosamente!')

        if is_ajax:
            return JsonResponse({'success': True})

        return redirect('administrador:listar_grupos')

    # Manejo de errores
    if is_ajax:
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]

        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)

    # Si no es AJAX
    for field, error_list in form.errors.items():
        for error in error_list:
            messages.error(request, f"{field}: {error}")

    return redirect('administrador:listar_grupos')


@require_POST
@login_required
def editar_grupo(request, grupo_id):
    """Edita un grupo existente con validaciones AJAX"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    form = GrupoForm(request.POST, instance=grupo, request=request)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if form.is_valid():
        grupo = form.save()

        # Notificar a administradores
        notificar_a_admins(
            mensaje=f'El grupo "{grupo.nombre}" fue editado.',
            tipo="WARNING",
            exclude_user=request.user,
            link=reverse("administrador:listar_grupos")
        )

        messages.success(
            request, f'Grupo "{grupo.nombre}" actualizado exitosamente!')

        if is_ajax:
            return JsonResponse({'success': True})

        return redirect('administrador:listar_grupos')

    # Manejo de errores
    if is_ajax:
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]

        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)

    # Si no es AJAX
    for field, error_list in form.errors.items():
        for error in error_list:
            messages.error(request, f"{field}: {error}")

    return redirect('administrador:listar_grupos')


@require_POST
@login_required
def eliminar_grupo(request, grupo_id):
    """Elimina un grupo si no tiene usuarios asociados"""
    grupo = get_object_or_404(Grupo, id=grupo_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Verificar si tiene usuarios asociados
    if grupo.usuarios.exists():
        msg = f'No se puede eliminar el grupo "{grupo.nombre}" porque tiene {grupo.usuarios.count()} usuario(s) asociado(s).'

        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': msg
            }, status=400)

        messages.error(request, msg)
        return redirect('administrador:listar_grupos')

    nombre_grupo = grupo.nombre
    grupo.delete()

    # Notificar a administradores
    notificar_a_admins(
        mensaje=f'El grupo "{nombre_grupo}" fue eliminado.',
        tipo="DANGER",
        exclude_user=request.user,
        link=reverse("administrador:listar_grupos")
    )

    msg = f'El grupo "{nombre_grupo}" fue eliminado exitosamente.'
    messages.info(request, msg)

    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': msg
        })

    messages.success(request, msg)
    return redirect('administrador:listar_grupos')


@login_required
def detalles_grupo_api(request, grupo_id):
    """API para obtener detalles de un grupo"""
    try:
        grupo = Grupo.objects.get(id=grupo_id)

        # Obtener usuarios del grupo
        usuarios = grupo.usuarios.all().values('id', 'username', 'email', 'estado')

        # Obtener roles asociados
        roles = grupo.roles_asociados.all().values('id', 'nombre', 'color')

        data = {
            'nombre': grupo.nombre,
            'descripcion': grupo.descripcion,
            'color': grupo.color,
            'lider': grupo.lider.username if grupo.lider else None,
            'lider_id': grupo.lider.id if grupo.lider else None,
            'es_departamento': grupo.es_departamento,
            'activo': grupo.activo,
            'fecha_creacion': grupo.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
            'usuarios_count': usuarios.count(),
            'roles_count': roles.count(),
            'usuarios': list(usuarios),
            'roles': list(roles)
        }

        return JsonResponse(data)

    except Grupo.DoesNotExist:
        return JsonResponse({'error': 'Grupo no encontrado'}, status=404)


@require_POST
@login_required
def asignar_usuario_grupo(request):
    """Asigna o remueve usuarios de grupos (AJAX)"""
    try:
        data = json.loads(request.body.decode("utf-8"))
        grupo_id = data.get("grupo_id")
        usuario_id = data.get("usuario_id")
        accion = data.get("accion")  # 'agregar' o 'remover'

        grupo = get_object_or_404(Grupo, id=grupo_id)
        usuario = get_object_or_404(User, id=usuario_id)

        if accion == 'agregar':
            grupo.usuarios.add(usuario)
            mensaje = f'Usuario {usuario.username} agregado al grupo {grupo.nombre}'
        elif accion == 'remover':
            grupo.usuarios.remove(usuario)
            mensaje = f'Usuario {usuario.username} removido del grupo {grupo.nombre}'
        else:
            return JsonResponse({"success": False, "message": "Acción no válida"})

        # Notificar
        notificar_a_admins(
            mensaje=f'{usuario.username} fue {accion} del grupo "{grupo.nombre}".',
            tipo="INFO",
            exclude_user=request.user
        )

        return JsonResponse({"success": True, "message": mensaje})

    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error: {str(e)}"})

# ======================================
# Vistas para Roles (Actualizadas)
# ======================================


@login_required
def listar_roles(request):
    """Lista todos los roles con permisos pre-cargados"""
    roles = Rol.objects.prefetch_related('permisos').all()
    permisos = Permission.objects.select_related('content_type').order_by(
        'content_type__app_label', 'name'
    )
    return render(request, 'includes/administrador/tablas/listar_roles.html', {
        'roles': roles,
        'permisos': permisos
    })


@require_POST
@login_required
def crear_rol(request):
    """Crea un nuevo rol con validaciones AJAX"""
    form = RolForm(request.POST)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if form.is_valid():
        rol = form.save()

        # Notificar a administradores
        notificar_a_admins(
            mensaje=f'Se ha creado un nuevo rol: "{rol.nombre}".',
            tipo="INFO",
            exclude_user=request.user,
            link=reverse("administrador:listar_roles")
        )

        messages.success(request, f'Rol "{rol.nombre}" creado exitosamente!')

        if is_ajax:
            return JsonResponse({'success': True})

        return redirect('administrador:listar_roles')

    # Manejo de errores
    if is_ajax:
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]

        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)

    # Si no es AJAX
    for field, error_list in form.errors.items():
        for error in error_list:
            messages.error(request, f"{field}: {error}")

    return redirect('administrador:listar_roles')


@require_POST
@login_required
def editar_rol(request, rol_id):
    """Edita un rol existente con validaciones AJAX"""
    rol = get_object_or_404(Rol, id=rol_id)
    form = RolForm(request.POST, instance=rol)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if form.is_valid():
        rol = form.save()

        # Notificar a administradores
        notificar_a_admins(
            mensaje=f'El rol "{rol.nombre}" fue editado.',
            tipo="WARNING",
            exclude_user=request.user,
            link=reverse("administrador:listar_roles")
        )

        messages.success(
            request, f'Rol "{rol.nombre}" actualizado exitosamente!')

        if is_ajax:
            return JsonResponse({'success': True})

        return redirect('administrador:listar_roles')

    # Manejo de errores
    if is_ajax:
        errors = {}
        for field, error_list in form.errors.items():
            errors[field] = [str(error) for error in error_list]

        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)

    # Si no es AJAX
    for field, error_list in form.errors.items():
        for error in error_list:
            messages.error(request, f"{field}: {error}")

    return redirect('administrador:listar_roles')


@require_POST
@login_required
def eliminar_rol(request, rol_id):
    """Elimina un rol si no tiene usuarios asociados"""
    rol = get_object_or_404(Rol, id=rol_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Verificar si tiene usuarios asociados
    if rol.user_set.exists():
        msg = f'No se puede eliminar el rol "{rol.nombre}" porque tiene {rol.user_set.count()} usuario(s) asociado(s).'

        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': msg
            }, status=400)

        messages.error(request, msg)
        return redirect('administrador:listar_roles')

    nombre_rol = rol.nombre
    rol.delete()

    # Notificar a administradores
    notificar_a_admins(
        mensaje=f'El rol "{nombre_rol}" fue eliminado.',
        tipo="DANGER",
        exclude_user=request.user,
        link=reverse("administrador:listar_roles")
    )

    msg = f'El rol "{nombre_rol}" fue eliminado exitosamente.'
    messages.info(request, msg)

    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': msg
        })

    messages.success(request, msg)
    return redirect('administrador:listar_roles')

# =============================================================
# VISTA PERSONALIZADA PARA CREAR USUARIOS CON EL ADMINISTRADOR
# =============================================================


class SimpleUserCreateView(CreateView):
    form_class = SimpleUserCreationForm
    template_name = 'administrador/crear_usuario.html'
    success_url = reverse_lazy('administrador:administrador_dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, f'Usuario "{self.object.username}" creado exitosamente!')
        # Notifica a los administradores sobre el nuevo usuario creado
        notificar_a_admins(
            mensaje=f'Se ha registrado a: "{self.object.username}".',
            tipo="INFO",
            exclude_user=self.request.user,
            # Para que el admin pueda ir a ver los usuarios creados
            link=reverse("administrador:administrador_dashboard")
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request, "Error al crear el usuario. Por favor revise los datos.")
        return super().form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['label_suffix'] = ''  # Elimina los dos puntos de las etiquetas
        return kwargs

# =============================================================
# VISTA PARA ASIGNAR ROL A USUARIOS DESDE EL ADMINISTRADOR
# =============================================================


@require_POST
@login_required
def asignar_rol_usuario(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        user_id = data.get("user_id")
        rol_id = data.get("rol_id")

        usuario = get_object_or_404(User, id=user_id)
        rol = get_object_or_404(Rol, id=rol_id)

        usuario.rol = rol
        # opcional: al asignar rol lo activas
        usuario.estado = "ACTIVO"
        usuario.save()
        # Notifica a los administradores sobre el nuevo rol asignado
        notificar_a_admins(
            mensaje=f'El usuario {usuario.username} fue asignado al rol "{rol.nombre}".',
            tipo="INFO",
            exclude_user=request.user
        )

        return JsonResponse({"success": True, "message": f"Rol '{rol.nombre}' asignado a {usuario.username}"})
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error: {str(e)}"})


# =============================================================
# VISTA PARA CAMBIAR EL ESTADO DE UN USUARIO (ACTIVO/INACTIVO)
# =============================================================
@csrf_exempt
@require_POST
def cambiar_estado_usuario(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'No autenticado'}, status=403)
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        estado = data.get('estado')
        user = User.objects.get(id=user_id)

        if user.is_superuser and estado != 'ACTIVO':
            return JsonResponse({'warning': False, 'message': 'No se puede desactivar un superusuario.'}, status=400)

        if estado == 'ACTIVO':
            user.estado = 'ACTIVO'
            user.is_active = True

        else:
            user.estado = 'INACTIVO'
            user.is_active = False

        user.save()
        notificar_a_admins(
            mensaje=f'El estado del usuario {user.username} fue cambiado a "{user.estado}"',
            tipo="WARNING" if user.estado == "INACTIVO" else "SUCCESS",
            exclude_user=request.user,
            link=reverse("administrador:administrador_dashboard")
        )

        return JsonResponse({'success': True, 'message': f'Estado actualizado a {user.estado} para {user.username}'})

    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Usuario no encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# ==============================================
# EDICIÓN DE PERFIL
# ==============================================
@login_required
def edit_profile(request):
    from .forms import CustomUserChangeForm

    form = CustomUserChangeForm(request.POST or None, instance=request.user)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            rol_slug = request.user.rol_nombre.lower().replace(" ", "-")
            nombre_url = f"{rol_slug}_dashboard"
            messages.success(request, "Perfil actualizado correctamente.")
            try:
                return redirect(nombre_url)
            except:
                return redirect('administrador:home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        request, f"Error en {form.fields[field].label}: {error}")

    return render(request, "registration/edit_profile.html", {"form": form})

# |=============================================
# | VISTAS DE GESTION DE PERMISOS Y ROLES
# |=============================================


@login_required
def gestion_permisos_masiva(request):
    """Asignación masiva de permisos a usuarios"""
    if not request.user.has_perm('auth.change_user'):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'No tienes permiso para realizar esta acción'
            }, status=403)
        messages.error(request, 'No tienes permiso para realizar esta acción')
        return redirect('administrador:administrador_dashboard')

    if request.method == 'POST':
        # Detectar si es AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            # Procesar el formulario
            usuarios_ids = request.POST.getlist('usuarios')
            permisos_ids = request.POST.getlist('permisos')
            rol_id = request.POST.get('rol', '')
            tipo_asignacion = request.POST.get('tipo_asignacion', 'rol')

            # Validaciones
            if not usuarios_ids:
                error_msg = 'Debes seleccionar al menos un usuario'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('administrador:gestion_masiva')

            if tipo_asignacion == 'rol' and not rol_id:
                error_msg = 'Debes seleccionar un rol'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('administrador:gestion_masiva')

            if tipo_asignacion == 'permisos' and not permisos_ids:
                error_msg = 'Debes seleccionar al menos un permiso'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('administrador:gestion_masiva')

            # Obtener objetos
            usuarios = User.objects.filter(id__in=usuarios_ids)

            # Verificar que existan los usuarios
            if not usuarios.exists():
                error_msg = 'No se encontraron los usuarios seleccionados'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
                return redirect('administrador:gestion_masiva')

            cambios = 0
            usuarios_afectados = []

            for usuario in usuarios:
                if tipo_asignacion == 'rol':
                    # Asignar rol
                    rol = Rol.objects.get(id=rol_id)
                    usuario.rol = rol
                    usuario.save()
                    cambios += 1
                    usuarios_afectados.append(usuario.username)

                    # Sincronizar con grupo de Django
                    if rol.grupo_django:
                        usuario.groups.add(rol.grupo_django)

                else:  # tipo_asignacion == 'permisos'
                    # Asignar permisos directos
                    permisos = Permission.objects.filter(id__in=permisos_ids)
                    if permisos.exists():
                        usuario.user_permissions.add(*permisos)
                        cambios += len(permisos)
                        usuarios_afectados.append(usuario.username)

            # Crear mensaje de éxito
            success_msg = f'Se realizaron {cambios} cambios en {usuarios.count()} usuario(s)'
            if usuarios_afectados:
                success_msg += f': {", ".join(usuarios_afectados[:3])}'
                if len(usuarios_afectados) > 3:
                    success_msg += f' y {len(usuarios_afectados) - 3} más'

            # AGREGAR MENSAJE DE ÉXITO usando Django messages
            messages.success(
                request, f'Se realizaron {cambios} cambios en {usuarios.count()} usuario(s).')

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': success_msg,
                    'redirect_url': reverse('administrador:gestion_masiva')
                })

            return redirect('administrador:gestion_masiva')

        except Rol.DoesNotExist:
            error_msg = 'El rol seleccionado no existe'
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_msg})
            messages.error(request, error_msg)
            return redirect('administrador:gestion_masiva')
        except Exception as e:
            error_msg = f'Error al procesar la solicitud: {str(e)}'
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_msg})
            messages.error(request, error_msg)
            return redirect('administrador:gestion_masiva')

    # GET: Mostrar formulario
    usuarios = User.objects.filter(estado='ACTIVO').select_related('rol')
    roles = Rol.objects.all()
    permisos = Permission.objects.select_related(
        'content_type').order_by('content_type__app_label', 'name')

    return render(request, 'administrador/gestion_masiva.html', {
        'usuarios': usuarios,
        'roles': roles,
        'permisos': permisos,
        'title': 'Asignación Masiva de Permisos'
    })


@login_required
def diagnosticar_permisos(request):
    """Asignación masiva de permisos a usuarios"""
    print(f"\n=== DEBUG: Vista gestion_permisos_masiva llamada ===")
    print(f"Método: {request.method}")
    print(
        f"Es AJAX: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")

    if not request.user.has_perm('auth.change_user'):
        print("DEBUG: Usuario sin permisos")
    """Vista temporal para diagnosticar la relación"""

    # Verificar las relaciones disponibles
    permiso = Permission.objects.first()
    if permiso:
        # Ver qué relaciones tiene
        print("Relaciones disponibles en Permission:")
        for field in Permission._meta.get_fields():
            print(f"  - {field.name}: {field}")

    return JsonResponse({'status': 'ok'})


@login_required
def reporte_permisos(request):
    """Genera reporte de permisos por rol/usuario"""
    roles = Rol.objects.prefetch_related('permisos', 'user_set').all()

    # Estadísticas
    total_usuarios = User.objects.count()
    usuarios_por_rol = []

    for rol in roles:
        usuarios_por_rol.append({
            'rol': rol.nombre,
            'cantidad': rol.user_set.count(),
            'color': rol.color,
            'permisos': rol.permisos.count()
        })

    # Primero obtenemos los permisos sin annotate
    permisos_comunes = Permission.objects.select_related('content_type').all()[
        :20]

    # Luego calculamos manualmente las estadísticas
    permisos_con_estadisticas = []

    for permiso in permisos_comunes:
        # 1. Usuarios con permiso directo
        usuarios_directos = User.objects.filter(
            user_permissions=permiso).count()

        # 2. Roles que tienen este permiso
        roles_con_permiso = Rol.objects.filter(permisos=permiso)
        roles_asignados = roles_con_permiso.count()

        # 3. Usuarios que tienen el permiso a través de roles
        usuarios_por_rol_permiso = 0
        for rol in roles_con_permiso:
            usuarios_por_rol_permiso += rol.user_set.count()

        # 4. Total de usuarios con este permiso
        total_usuarios_permiso = usuarios_directos + usuarios_por_rol_permiso

        # Agregar atributos al permiso
        permiso.usuarios_directos = usuarios_directos
        permiso.roles_asignados = roles_asignados
        permiso.usuarios_por_rol = usuarios_por_rol_permiso
        permiso.total_usuarios = total_usuarios_permiso
        permiso.roles_lista = roles_con_permiso  # Para usar en el template

        permisos_con_estadisticas.append(permiso)

    # Usuarios sin rol
    usuarios_sin_rol = User.objects.filter(
        rol__isnull=True, is_superuser=False).count()

    return render(request, 'administrador/reporte_permisos.html', {
        'roles': roles,
        'usuarios_por_rol': usuarios_por_rol,
        'permisos_comunes': permisos_con_estadisticas,
        'total_usuarios': total_usuarios,
        'usuarios_sin_rol': usuarios_sin_rol
    })

# |=============================================
# | VISTA PARA DETALLES DE ROL (API)
# |=============================================


@login_required
def detalles_rol_api(request, rol_id):
    """API para obtener detalles de un rol"""
    try:
        rol = Rol.objects.get(id=rol_id)

        # Obtener usuarios con este rol
        usuarios = User.objects.filter(rol=rol).values(
            'id', 'username', 'email', 'estado')

        # Obtener permisos
        permisos = rol.permisos.values(
            'id', 'name', 'codename', 'content_type__app_label')

        data = {
            'nombre': rol.nombre,
            'descripcion': rol.descripcion,
            'color': rol.color,
            'creado': rol.creado.strftime('%d/%m/%Y %H:%M'),
            'usuarios_count': usuarios.count(),
            'permisos_count': permisos.count(),
            'usuarios': list(usuarios[:10]),  # Limitar a 10 usuarios
            'permisos': list(permisos)
        }

        return JsonResponse(data)

    except Rol.DoesNotExist:
        return JsonResponse({'error': 'Rol no encontrado'}, status=404)


# |=============================================
# | VISTA DE PRUEBA DE TOASTS


@login_required
def test_toast(request):
    messages.success(request, "¡Toast de prueba funciona correctamente! 🎉")
    messages.warning(request, "Este es un mensaje de advertencia. ⚠️")
    messages.error(request, "Este es un mensaje de error. ❌")
    messages.info(request, "Novedades disponibles 📢")
    return redirect("administrador:home")


# views.py (temporal - elimina después)
@login_required
def test_ajax(request):
    """Vista temporal para testear AJAX"""
    if request.method == 'POST':
        print("Test AJAX - Datos recibidos:", dict(request.POST))
        return JsonResponse({
            'success': True,
            'message': 'Test exitoso!',
            'data_received': dict(request.POST)
        })

    return JsonResponse({'error': 'Solo POST permitido'})
