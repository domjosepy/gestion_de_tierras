from django.urls import path
from . import views

app_name = 'digitalizador'

urlpatterns = [
    path('dashboard/', views.digitalizador_dashboard,
         name='digitalizador_dashboard'),
    path('tarea/<int:tarea_id>/', views.detalle_tarea, name='detalle_tarea'),
    path('tarea/<int:tarea_id>/iniciar/',
         views.iniciar_digitalizacion, name='iniciar_digitalizacion'),
    path('tarea/<int:tarea_id>/subir-precat/',
         views.subir_precat, name='subir_precat'),
    path('descargar/precat/<int:archivo_id>/',
         views.descargar_precat,
         name='descargar_precat'),
    path('archivos/', views.listar_archivos_digitalizador,
         name='listar_archivos_digitalizador'),
    path('descargar/<int:archivo_id>/', views.descargar_archivo_digitalizador,
         name='descargar_archivo_digitalizador'),

]
