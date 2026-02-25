from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    LoginView, HomeView, AdminView, InvitadoView, SignUpView,
    CustomPasswordChangeView, edit_profile, test_toast,
    SimpleUserCreateView,
    asignar_rol_usuario, cambiar_estado_usuario,
    listar_roles, crear_rol, editar_rol, eliminar_rol,
    gestion_permisos_masiva, reporte_permisos, detalles_rol_api, test_ajax,
    listar_grupos, crear_grupo, editar_grupo, eliminar_grupo, detalles_grupo_api, asignar_usuario_grupo,
    listar_tipos_objetivo, crear_tipo_objetivo, editar_tipo_objetivo, eliminar_tipo_objetivo, detalles_tipo_objetivo_api)

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

    # ------------------------------------
    # 6. Vistas de Grupos
    # ------------------------------------
    path('grupos/', listar_grupos, name='listar_grupos'),
    path('grupos/crear/', crear_grupo, name='crear_grupo'),
    path('grupos/editar/<int:grupo_id>/', editar_grupo, name='editar_grupo'),
    path('grupos/eliminar/<int:grupo_id>/',
         eliminar_grupo, name='eliminar_grupo'),
    path('grupos/detalles/<int:grupo_id>/',
         detalles_grupo_api, name='detalles_grupo_api'),
    path('grupos/asignar-usuario/', asignar_usuario_grupo,
         name='asignar_usuario_grupo'),

    # ------------------------------------
    # 7. Vistas de Tipos de Objetivo
    # ------------------------------------
    path('tipos-objetivo/', listar_tipos_objetivo, name='listar_tipos_objetivo'),
    path('tipos-objetivo/crear/', crear_tipo_objetivo, name='crear_tipo_objetivo'),
    path('tipos-objetivo/editar/<int:tipo_objetivo_id>/', editar_tipo_objetivo, name='editar_tipo_objetivo'),
    path('tipos-objetivo/eliminar/<int:tipo_objetivo_id>/', eliminar_tipo_objetivo, name='eliminar_tipo_objetivo'),
    path('tipos-objetivo/detalles/<int:tipo_objetivo_id>/', detalles_tipo_objetivo_api, name='detalles_tipo_objetivo_api'),

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
