from django.urls import path
from . import views
from core.views import DepartamentoListView, DepartamentoCreateView, editar_departamento, eliminar_departamento

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
    path('departmento/editar/<int:departamento_id>/',
         editar_departamento, name='editar_departamento'),
    path('departamento/eliminar/<int:departamento_id>/',
         eliminar_departamento, name='eliminar_departamento'),

]
