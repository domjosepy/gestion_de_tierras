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
from django.shortcuts import render, get_list_or_404, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy, NoReverseMatch
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView, CreateView, ListView
from core.notificaciones.utils import notificar_a_admins

# Local application imports
from .forms import CustomUserCreationForm, CustomPasswordChangeForm, SimpleUserCreationForm
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

            # por ejemplo
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
        try:
            return reverse_lazy(nombre_url)
        except NoReverseMatch:
            return reverse_lazy("home")

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
    success_url = reverse_lazy("login")
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
            return reverse_lazy('home')

    def form_valid(self, form):
        messages.success(
            self.request,
            "¡Tu contraseña ha sido cambiada exitosamente!"
        )
        return super().form_valid(form)

# ======================================
# Vistas para Roles
# =======================================


class RolListView(LoginRequiredMixin, ListView):
    model = Rol
    template_name = 'administrador/listar_roles.html'
    context_object_name = 'roles'


class RolCreateView(LoginRequiredMixin, CreateView):
    model = Rol
    fields = ['nombre', 'descripcion', 'color', 'permisos']
    template_name = 'includes/administrador/modal/roles/crear_rol_modal.html'

    def get_success_url(self):
        # Redirige a la página anterior si existe, si no a listar_roles
        return self.request.META.get('HTTP_REFERER', str(reverse_lazy('listar_roles')))

    def form_valid(self, form):
        # Guardar el rol sin los permisos primero
        rol = form.save(commit=False)
        rol.save()

        # Capturar los permisos enviados desde el formulario
        permisos_ids = self.request.POST.getlist('permisos')
        if permisos_ids:
            rol.permisos.set(permisos_ids)

        # Mensaje de éxito
        messages.success(
            self.request, f'Rol "{rol.nombre}" creado exitosamente!'
        )

        # Notificar a los admins
        notificar_a_admins(
            mensaje=f'Se ha creado un nuevo rol: "{rol.nombre}".',
            tipo="INFO",
            exclude_user=self.request.user,

            link=reverse("listar_roles")
        )

        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, 'Error al crear el rol. Por favor revise los datos.'
        )
        return super().form_invalid(form)


def editar_rol(request, rol_id):
    rol = get_object_or_404(Rol, id=rol_id)
    if request.method == 'POST':
        rol.nombre = request.POST.get('nombre')
        rol.descripcion = request.POST.get('descripcion')
        permisos_ids = request.POST.getlist('permisos')
        rol.permisos.set(permisos_ids)
        rol.save()
        messages.success(request, "Rol actualizado correctamente.")
        notificar_a_admins(
            mensaje=f'El rol "{rol.nombre}" fue editado.',
            tipo="WARNING",
            exclude_user=request.user
        )
        return redirect('listar_roles')
    return redirect('listar_roles')


def eliminar_rol(request, rol_id):
    rol = get_object_or_404(Rol, id=rol_id)
    if rol.user_set.exists():
        messages.error(
            request, "Este rol está asignado a uno o más usuarios y no puede ser eliminado.")
    else:
        rol.delete()
        messages.success(request, "Rol eliminado correctamente.")
    return redirect('listar_roles')

# =============================================================
# VISTA PERSONALIZADA PARA CREAR USUARIOS CON EL ADMINISTRADOR
# =============================================================


class SimpleUserCreateView(CreateView):
    form_class = SimpleUserCreationForm
    template_name = 'administrador/crear_usuario.html'
    success_url = reverse_lazy('administrador_dashboard')

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
            link=reverse("administrador_dashboard")
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
            link=reverse("administrador_dashboard")
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
                return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        request, f"Error en {form.fields[field].label}: {error}")

    return render(request, "registration/edit_profile.html", {"form": form})


@login_required
def test_toast(request):
    messages.success(request, "¡Toast de prueba funciona correctamente! 🎉")
    messages.warning(request, "Este es un mensaje de advertencia. ⚠️")
    messages.error(request, "Este es un mensaje de error. ❌")
    messages.info(request, "Novedades disponibles 📢")
    return redirect("home")
