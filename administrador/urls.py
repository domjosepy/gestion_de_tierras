from django.urls import path
from .views import (
    LoginView, HomeView, AdminView, InvitadoView, SignUpView,
    CustomPasswordChangeView, edit_profile, test_toast,
    SimpleUserCreateView,
    asignar_rol_usuario, cambiar_estado_usuario,
    listar_roles, crear_rol, editar_rol, eliminar_rol,
    gestion_permisos_masiva, reporte_permisos, detalles_rol_api, test_ajax
)
from django.contrib.auth.views import LogoutView

app_name = 'administrador'

urlpatterns = [
    # -------------------------------------
    # 1. Autenticación y Cuenta de Usuario
    # -------------------------------------
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='administrador:login'), name='logout'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('password_change/', CustomPasswordChangeView.as_view(),
         name='password_change'),
    path('profile/edit/', edit_profile, name='edit_profile'),
    path('test-toast/', test_toast, name='test_toast'),


    # ------------------------------------
    # 2. Vistas Principales y Redirección
    # ------------------------------------
    path('home/', HomeView.as_view(), name='home'),
    path('administrador-dashboard/', AdminView.as_view(),
         name='administrador_dashboard'),
    path('invitado-dashboard/', InvitadoView.as_view(), name='invitado_dashboard'),


    # ------------------------------------
    # 3. Vistas de Roles
    # ------------------------------------
    path('roles/', listar_roles, name='listar_roles'),
    path('roles/crear/', crear_rol, name='crear_rol'),
    path('roles/editar/<int:rol_id>/', editar_rol, name='editar_rol'),
    path('roles/eliminar/<int:rol_id>/', eliminar_rol, name='eliminar_rol'),


    # ---------------------------------------------
    # 4. Vistas de Crear usuario Form desde admin
    # --------------------------------------------
    path('usuarios/crear/', SimpleUserCreateView.as_view(), name='crear_usuario'),

    # ---------------------------------------------
    # 5. Vistas de Asignar Rol
    # --------------------------------------------
    path('asignar-rol/', asignar_rol_usuario, name='asignar_rol'),

    # Cambiar estado de usuario para AJAX del switch
    path('cambiar_estado_usuario/', cambiar_estado_usuario,
         name='cambiar_estado_usuario'),

    # Gestión masiva y reportes
    path('permisos/masiva/', gestion_permisos_masiva, name='gestion_masiva'),
    path('permisos/reporte/', reporte_permisos, name='reporte_permisos'),
    path('roles/detalles/<int:rol_id>/',
         detalles_rol_api, name='detalles_rol_api'),

]
