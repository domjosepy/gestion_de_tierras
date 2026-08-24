from django.urls import path
from analisis.views import (analisis_dashboard, analisis_solicitudes, obtener_datos_relevamiento_analisis, relevamiento_asignar_analista,
    colonias_relevadas_analisis, cambiar_analista_asignacion, eliminar_asignacion_analista,
    detalle_asignacion_relevamiento, validar_analisis_colonia,
    generar_dictamen_analisis
)

app_name = 'analisis'
urlpatterns = [
    # INICIO
    path('analisis_dashboard/', analisis_dashboard, name='analisis_dashboard'),
    # LISTA DE SOLICITUDES
    path('solicitudes/', analisis_solicitudes, name='solicitudes_relevamiento_analisis'),
    # COLONIAS RELEVADAS (3 tablas desde AsignacionAnalisis)
    path('colonias-relevadas/', colonias_relevadas_analisis, name='colonias_relevadas_analisis'),
    path('solicitud/<int:solicitud_id>/detalle-asignacion/', detalle_asignacion_relevamiento, name='detalle_asignacion_relevamiento'),
    # API: datos de relevamiento finalizado para el modal
    path('relevamiento-detalle/<int:pk>/', obtener_datos_relevamiento_analisis, name='obtener_datos_relevamiento_analisis'),
    # ASIGNACIÓN DE ANALISTA (nueva asignación)
    path('solicitud/<int:solicitud_id>/asignar-analista/', relevamiento_asignar_analista, name='asignar_analista'),
    # CAMBIAR ANALISTA (cancela la actual, crea nueva)
    path('asignacion/<int:asignacion_id>/cambiar-analista/', cambiar_analista_asignacion, name='cambiar_analista_asignacion'),
    # TERMINAR ASIGNACIÓN
    path('solicitud/<int:solicitud_id>/eliminar-asignacion/', eliminar_asignacion_analista, name='eliminar_asignacion_analista'),
    # ACCIONES DEL DETALLE DE ANALISIS
    path('solicitud/<int:solicitud_id>/validar-analisis/', validar_analisis_colonia, name='validar_analisis_colonia'),
    path('solicitud/<int:solicitud_id>/generar-dictamen/', generar_dictamen_analisis, name='generar_dictamen_analisis'),
]