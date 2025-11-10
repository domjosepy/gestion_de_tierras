from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # DEPARTAMENTOS - GERENCIA

    # AREAS - ADMINISTRADOR / GERENCIA
    # path("areas/", views.AreaListView, name="areas_list"),
    # path("areas/nuevo/", views.AreaCreateView, name="areas_create"),
    # path("areas/<int:pk>/editar/", views.AreaUpdateView, name="areas_edit"),
    # path("areas/<int:pk>/eliminar/", views.AreaDeleteView, name="areas_delete"),

    # OBJETIVOS - GERENCIA
    # path("objetivos/", views.ObjetivoListView, name="objetivos_list"),
    # path("objetivos/nuevo/", views.ObjetivoCreateView, name="objetivos_create"),
    # path("objetivos/<int:pk>/editar/", views.ObjetivoUpdateView, name="objetivos_edit"),
    # path("objetivos/<int:pk>/eliminar/", views.ObjetivoDeleteView, name="objetivos_delete"),

    # SOLICITUDES - GERENCIA
    # path("solicitudes/", views.SolicitudListView, name="solicitudes_list"),
    # path("solicitudes/nuevo/", views.SolicitudCreateView, name="solicitudes_create"),
    # path("solicitudes/<int:pk>/editar/", views.SolicitudUpdateView, name="solicitudes_edit"),
    # path("solicitudes/<int:pk>/eliminar/", views.SolicitudDeleteView, name="solicitudes_delete"),

    # RELEVAMIENTOS - CAMPO
    # path("relevamientos/", views.RelevamientoListView, name="relevamientos_list"),
    # path("relevamientos/nuevo/", views.RelevamientoCreateView, name="relevamientos_create"),
    # path("relevamientos/<int:pk>/editar/", views.RelevamientoUpdateView, name="relevamientos_edit"),
    # path("relevamientos/<int:pk>/detalles/", views.RelevamientoDetailView, name="relevamientos_detail"),
    # path("relevamientos/<int:pk>/eliminar/", views.RelevamientoDeleteView, name="relevamientos_delete"),
    # ... rutas para departamentos, areas, objetivos, solicitudes, relevamientos
]
