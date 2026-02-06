from django.urls import path
from sig.views import (
    listar_archivos_precat, sig_dashboard, detalle_solicitud, asignar_usuario_solicitud,
    iniciar_digitalizacion, finalizar_digitalizacion, revisar_solicitud,
    obtener_estados_dashboard, cargar_tabla_estado, cambiar_usuario_solicitud, eliminar_asignacion, sig_solicitudes,
    descargar_archivo_precat, obtener_archivos_solicitud, aprobar_para_campo,
    aprobar_digitalizacion, rechazar_digitalizacion, devolver_para_correccion
)

app_name = 'sig'

urlpatterns = [
    path('sig-dashboard/', sig_dashboard, name='sig_dashboard'),
    path('solicitudes/', sig_solicitudes, name='solicitudes_relevamiento_sig'),
    path('solicitud/<int:solicitud_id>/',
         detalle_solicitud, name='detalle_solicitud'),
    path('solicitud/<int:solicitud_id>/asignar-usuario/',
         asignar_usuario_solicitud, name='asignar_usuario_solicitud'),
    path('solicitud/<int:solicitud_id>/cambiar-usuario/',
         cambiar_usuario_solicitud, name='cambiar_usuario_solicitud'),
    path('solicitud/<int:solicitud_id>/eliminar-asignacion/',
         eliminar_asignacion, name='eliminar_asignacion'),
    path('solicitud/<int:solicitud_id>/iniciar-digitalizacion/',
         iniciar_digitalizacion, name='iniciar_digitalizacion'),
    path('solicitud/<int:solicitud_id>/finalizar-digitalizacion/',
         finalizar_digitalizacion, name='finalizar_digitalizacion'),
    path('solicitud/<int:solicitud_id>/aprobar-campo/',
         aprobar_para_campo, name='aprobar_para_campo'),
    path('solicitud/<int:solicitud_id>/revisar/',
         revisar_solicitud, name='revisar_solicitud'),
    path('dashboard/estados/', obtener_estados_dashboard,
         name='obtener_estados_dashboard'),
    path('dashboard/tabla/<str:estado>/',
         cargar_tabla_estado, name='cargar_tabla_estado'),

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
