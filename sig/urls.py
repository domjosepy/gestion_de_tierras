# sig/urls.py
from django.urls import path
from . import views

app_name = 'sig'

urlpatterns = [
    path('sig-dashboard/', views.sig_dashboard, name='sig_dashboard'),
    path('solicitud/<int:solicitud_id>/',
         views.detalle_solicitud, name='detalle_solicitud'),
    path('solicitud/<int:solicitud_id>/asignar/',
         views.asignar_digitalizador, name='asignar_digitalizador'),
]
