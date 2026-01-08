# digitalizador/urls.py
from django.urls import path
from . import views

app_name = 'digitalizador'

urlpatterns = [
    path('digitalizador-dashboard/', views.digitalizador_dashboard,
         name='digitalizador_dashboard'),
    path('tarea/<int:tarea_id>/', views.detalle_tarea, name='detalle_tarea'),
    path('tarea/<int:tarea_id>/iniciar/',
         views.iniciar_digitalizacion, name='iniciar_digitalizacion'),
    path('tarea/<int:tarea_id>/finalizar/',
         views.finalizar_digitalizacion, name='finalizar_digitalizacion'),
]
