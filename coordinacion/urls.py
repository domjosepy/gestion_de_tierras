from django.urls import path
from .views import (dashboard_coordinacion, solicitudes_pendientes, generar_orden_view,
                    ordenes_trabajo, detalle_orden, asignar_equipos_orden, asignar_equipo_campo,
                    equipos_relevamiento, crear_equipo, reportes_coordinacion)

app_name = 'coordinacion'

urlpatterns = [
    # Dashboard
    path('dashboard/', dashboard_coordinacion, name='coordinacion_dashboard'),

    # Solicitudes
    path('solicitudes/', solicitudes_pendientes, name='solicitudes_pendientes'),
    path('generar-orden/<int:solicitud_id>/',
         generar_orden_view, name='generar_orden'),

    # Órdenes de trabajo
    path('ordenes/', ordenes_trabajo, name='ordenes_trabajo'),
    path('orden/<int:orden_id>/', detalle_orden, name='detalle_orden'),
    path('orden/<int:orden_id>/asignar-equipos/',
         asignar_equipos_orden, name='asignar_equipos'),
    path('api/asignar-equipo-campo/<int:solicitud_id>/',
         asignar_equipo_campo,
         name='api_asignar_equipo_campo'),

    # Equipos
    path('equipos/', equipos_relevamiento, name='equipos_relevamiento'),
    path('equipos/crear/', crear_equipo, name='crear_equipo'),

    # Reportes
    path('reportes/', reportes_coordinacion, name='reportes'),
]
