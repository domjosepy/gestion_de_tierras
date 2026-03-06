from django.urls import path
from .views import (dashboard_coordinacion, solicitudes_pendientes, solicitudes_canceladas, reactivar_orden,
                    generar_orden_view, ordenes_trabajo, detalle_orden,
                    modificar_orden, cancelar_orden, reportes_coordinacion,
                    asignar_personal_orden, control_relevamiento_panel, control_relevamiento_obtener_mermas)

app_name = 'coordinacion'

urlpatterns = [
    # Dashboard ok
    path('dashboard/', dashboard_coordinacion, name='coordinacion_dashboard'),

    # Solicitudes pendientes, canceladas, generar_orden, reactivar ok
    path('solicitudes/pendientes/', solicitudes_pendientes,
         name='solicitudes_pendientes'),
    path('solicitudes/canceladas/', solicitudes_canceladas,
         name='solicitudes_canceladas'),
    path('generar-orden/<int:solicitud_id>/',
         generar_orden_view, name='generar_orden'),
    path('solicitud/<int:orden_id>/reactivar/',
         reactivar_orden, name='reactivar_orden'),

    # Órdenes de trabajo
    path('ordenes/', ordenes_trabajo, name='ordenes_trabajo'),
    path('orden/<int:orden_id>/', detalle_orden, name='detalle_orden'),



    path('orden/<int:orden_id>/modificar/',
         modificar_orden, name='modificar_orden'),
    path('orden/<int:orden_id>/cancelar/',
         cancelar_orden, name='cancelar_orden'),

    # Reportes
    path('reportes/', reportes_coordinacion, name='reportes'),

    path('orden/<int:orden_id>/asignar-personal/',
         asignar_personal_orden, name='asignar_personal_orden'),

    # Control de Relevamiento (Gestión de Mermas)
    path('control-relevamiento/', control_relevamiento_panel, name='control_relevamiento_panel'),
    path('control-relevamiento/mermas/<int:colonia_id>/', 
         control_relevamiento_obtener_mermas, name='control_relevamiento_obtener_mermas'),

]
