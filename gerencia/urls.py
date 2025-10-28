from django.urls import path
from . import views
from core.views import (
    DepartamentoListView, DepartamentoCreateView, editar_departamento, eliminar_departamento,
    DistritoListView, DistritoCreateView, editar_distrito, eliminar_distrito,
    ColoniaListView, ColoniaCreateView, editar_colonia, eliminar_colonia
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
    path('departamento/crear/', DepartamentoCreateView.as_view(),
         name='crear_departamento'),
    path('departamento/editar/<int:departamento_id>/',
         editar_departamento, name='editar_departamento'),
    path('departamento/eliminar/<int:departamento_id>/',
         eliminar_departamento, name='eliminar_departamento'),

    # ------------------------------------
    # 3. Vistas de distritos
    # ------------------------------------
    path('distritos/', DistritoListView.as_view(), name='listar_distritos'),
    path('distrito/crear/', DistritoCreateView.as_view(), name='crear_distrito'),
    path('distrito/editar/<int:distrito_id>/',
         editar_distrito, name='editar_distrito'),
    path('distrito/eliminar/<int:distrito_id>/',
         eliminar_distrito, name='eliminar_distrito'),

    # ------------------------------------
    # 4. Vistas de colonias
    # ------------------------------------
    path('colonias/', ColoniaListView.as_view(), name='listar_colonias'),
    path('colonia/crear/', ColoniaCreateView.as_view(), name='crear_colonia'),
    path('colonia/editar/<int:colonia_id>/',
         editar_colonia, name='editar_colonia'),
    path('colonia/eliminar/<int:colonia_id>/',
         eliminar_colonia, name='eliminar_colonia'),


]
