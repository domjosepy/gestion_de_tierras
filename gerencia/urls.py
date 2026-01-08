from django.urls import path
from . import views
from core.views import (
    DepartamentoListView, crear_departamento, editar_departamento, eliminar_departamento,
    listar_distritos, crear_distrito, editar_distrito, eliminar_distrito,
    ColoniaListView, crear_colonia, editar_colonia, eliminar_colonia
)
from gerencia.views import (
    lista_solicitudes_relevamiento, obtener_datos_solicitud, crear_solicitud_relevamiento,
    editar_solicitud_relevamiento, eliminar_solicitud_relevamiento
)

app_name = "gerencia"

urlpatterns = [
    path('gerente-dashboard/', views.GerenciaView.as_view(),
         name='gerente_dashboard'),

    # ------------------------------------
    # 2. Vistas de departamentos
    # ------------------------------------
    path('departamentos/', DepartamentoListView.as_view(),
         name='listar_departamentos'),
    path('departamentos/crear/', crear_departamento,
         name='crear_departamento'),
    path('departamentos/editar/<int:departamento_id>/',
         editar_departamento, name='editar_departamento'),
    path('departamentos/eliminar/<int:departamento_id>/',
         eliminar_departamento, name='eliminar_departamento'),

    # ------------------------------------
    # 3. Vistas de distritos
    # ------------------------------------
    path('distritos/', listar_distritos, name='listar_distritos'),
    path('distritos/crear/', crear_distrito, name='crear_distrito'),
    path('distritos/editar/<int:pk>/',
         editar_distrito, name='editar_distrito'),
    path('distritos/eliminar/<int:pk>/',
         eliminar_distrito, name='eliminar_distrito'),

    # ------------------------------------
    # 4. Vistas de colonias
    # ------------------------------------
    path('colonias/', ColoniaListView.as_view(), name='listar_colonias'),
    path('colonias/crear/', crear_colonia, name='crear_colonia'),
    path('colonias/editar/<int:colonia_id>/',
         editar_colonia, name='editar_colonia'),
    path('colonias/eliminar/<int:colonia_id>/',
         eliminar_colonia, name='eliminar_colonia'),

    # ------------------------------------
    # 5. Vistas de solicitudes de relevamiento
    # ------------------------------------
    path('solicitudes-relevamiento/', lista_solicitudes_relevamiento,
         name='lista_solicitudes_relevamiento'),
    path('solicitudes-relevamiento/<int:pk>/datos/',
         obtener_datos_solicitud, name='obtener_datos_solicitud'),
    path('solicitudes-relevamiento/crear/<int:colonia_id>/',
         crear_solicitud_relevamiento, name='crear_solicitud_relevamiento'),
    path('solicitudes-relevamiento/<int:pk>/editar/',
         editar_solicitud_relevamiento, name='editar_solicitud_relevamiento'),
    path('solicitudes-relevamiento/<int:pk>/eliminar/',
         eliminar_solicitud_relevamiento, name='eliminar_solicitud_relevamiento'),
    # ------------------------------------
    # 6. API endpoints
    path('api/colonias/<int:colonia_id>/info/',
         views.api_info_colonia, name='api_info_colonia'),
]
