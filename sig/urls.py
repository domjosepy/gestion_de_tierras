# sig/urls.py
from django.urls import path
from sig.views import (sig_dashboard, detalle_solicitud, asignar_usuario_solicitud,
                       iniciar_digitalizacion, finalizar_digitalizacion, revisar_solicitud)

app_name = 'sig'

urlpatterns = [
    path('sig-dashboard/', sig_dashboard, name='sig_dashboard'),
    path('solicitud/<int:solicitud_id>/',
         detalle_solicitud, name='detalle_solicitud'),
    path('solicitud/<int:solicitud_id>/asignar-usuario/',
         asignar_usuario_solicitud, name='asignar_usuario_solicitud'),
    path('solicitud/<int:solicitud_id>/iniciar-digitalizacion/',
         iniciar_digitalizacion, name='iniciar_digitalizacion'),
    path('solicitud/<int:solicitud_id>/finalizar-digitalizacion/',
         finalizar_digitalizacion, name='finalizar_digitalizacion'),
    path('solicitud/<int:solicitud_id>/revisar/',
         revisar_solicitud, name='revisar_solicitud'),

]
