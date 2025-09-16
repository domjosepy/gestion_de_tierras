from django.urls import path
from .views import LoginView, HomeView, AdminView, InvitadoView, SignUpView, CustomPasswordChangeView, edit_profile, test_toast, RolListView, RolCreateView, RolUpdateView, RolDeleteView, SimpleUserCreateView, asignar_rol_usuario, cambiar_estado_usuario
from django.contrib.auth.views import LogoutView

urlpatterns = [
    # -------------------------------------
    # 1. Autenticación y Cuenta de Usuario
    # -------------------------------------
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('password_change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('test-toast/', test_toast, name='test_toast'),
  
    
    # ------------------------------------
    # 2. Vistas Principales y Redirección
    # ------------------------------------
    path('home/', HomeView.as_view(), name='home'),
    path('administrador-dashboard/', AdminView.as_view(), name='administrador_dashboard'),
    path('invitado-dashboard/', InvitadoView.as_view(), name='invitado_dashboard'),


    #------------------------------------
    # 3. Vistas de Roles
    # ------------------------------------
    path('roles/', RolListView.as_view(), name='listar_roles'),
    path('roles/crear/', RolCreateView.as_view(), name='crear_rol'),
    path('roles/editar/<int:pk>/', RolUpdateView.as_view(), name='editar_rol'),
    path('roles/eliminar/<int:pk>/', RolDeleteView.as_view(), name='eliminar_rol'),

    #---------------------------------------------
    # 4. Vistas de Crear usuario Form desde admin
    # --------------------------------------------
    path('usuarios/crear/', SimpleUserCreateView.as_view(), name='crear_usuario'),

    #---------------------------------------------
    # 5. Vistas de Asignar Rol
    # --------------------------------------------
    path('asignar-rol/', asignar_rol_usuario, name='asignar_rol'),

    # Cambiar estado de usuario para AJAX del switch
    path('cambiar_estado_usuario/', cambiar_estado_usuario, name='cambiar_estado_usuario'),

    # =========================================
    # Asegúrate de tener una vista basada en clase para crear usuarios, por ejemplo UserCreateView
    # path('usuarios/crear/', UserCreateView.as_view(), name='crear_usuario'),

    # Si solo tienes el formulario, primero crea una vista basada en clase en views.py que use SimpleUserCreationForm
    # Luego importa esa vista aquí y usa:
    # path('usuarios/crear/', TuVistaDeCreacionDeUsuario.as_view(), name='crear_usuario'),
]
