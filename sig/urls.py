from django.urls import path
from sig.views import (
    listar_archivos_precat, sig_dashboard, detalle_solicitud, asignar_usuario_solicitud,
    cambiar_usuario_solicitud, eliminar_asignacion, sig_solicitudes,
    descargar_archivo_precat, obtener_archivos_solicitud,
    aprobar_digitalizacion, rechazar_digitalizacion, devolver_para_correccion
)

app_name = 'sig'

urlpatterns = [
    # INICIO
    path('sig-dashboard/', sig_dashboard, name='sig_dashboard'),
    # LISTA DE SOLICITUDES
    path('solicitudes/', sig_solicitudes, name='solicitudes_relevamiento_sig'),
    # DETALLE SOLICITUD
    path('solicitud/<int:solicitud_id>/',
         detalle_solicitud, name='detalle_solicitud'),
    # ASIGANAR USUARIO - CAMBIAR - ELIMINAR
    path('solicitud/<int:solicitud_id>/asignar-usuario/',
         asignar_usuario_solicitud, name='asignar_usuario_solicitud'),
    path('solicitud/<int:solicitud_id>/cambiar-usuario/',
         cambiar_usuario_solicitud, name='cambiar_usuario_solicitud'),
    path('solicitud/<int:solicitud_id>/eliminar-asignacion/',
         eliminar_asignacion, name='eliminar_asignacion'),
    path('archivos-precat/', listar_archivos_precat,
         name='listar_archivos_precat'),
    path('descargar-precat/<int:archivo_id>/',
         descargar_archivo_precat, name='descargar_archivo_precat'),
    path('solicitud/<int:solicitud_id>/archivos/',
         obtener_archivos_solicitud, name='obtener_archivos_solicitud'),

    # En urls.py, si necesitas endpoints específicos para aprobar/rechazar
    path('solicitud/<int:solicitud_id>/aprobar-digitalizacion/',
         aprobar_digitalizacion, name='aprobar_digitalizacion'),
    path('solicitud/<int:solicitud_id>/rechazar-digitalizacion/',
         rechazar_digitalizacion, name='rechazar_digitalizacion'),
    path('solicitud/<int:solicitud_id>/devolver-correccion/',
         devolver_para_correccion, name='devolver_correccion'),
]
