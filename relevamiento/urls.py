from django.urls import path
from relevamiento.views import (
    encuestador_dashboard,
    formulario_desde_orden,
    editar_encuesta_relevamiento,
    resumen_relevamiento,
    coordinador_campo_dashboard,
    habilitar_formulario_relevamiento,
    finalizar_orden_campo,
    subcoordinador_dashboard,
    subcoordinador_upload,
    agregar_fotos,
)

app_name = "relevamiento"

urlpatterns = [
    # coordinador de campo
    path("coordinador-campo/dashboard/", coordinador_campo_dashboard, name="coordinador_dashboard"),
    path("coordinador-campo/orden/<int:orden_id>/habilitar-formulario/", 
         habilitar_formulario_relevamiento, name="habilitar_formulario"),
    path("coordinador-campo/orden/<int:orden_id>/finalizar/", 
         finalizar_orden_campo, name="finalizar_orden_campo"),


    # Dashboard del encuestador
    path("dashboard/", encuestador_dashboard, name="encuestador_dashboard"),

    # Dashboard Subcoordinador
    path("subcoordinador/dashboard/", subcoordinador_dashboard, name="subcoordinador_dashboard"),
    path("subcoordinador/upload/", subcoordinador_upload, name="subcoordinador_upload"),

    # Crear relevamiento SOLO desde una orden de trabajo (OBLIGATORIO)
    path("orden/<int:orden_id>/nueva-encuesta/", formulario_desde_orden, name="formulario_desde_orden"),

    # Editar relevamiento existente
    path("<int:pk>/editar/", editar_encuesta_relevamiento, name="edit"),

    # Resumen / detalle
    path("<int:pk>/", resumen_relevamiento, name="resumen_relevamiento"),
    path("<int:pk>/fotos/agregar/", agregar_fotos, name="agregar_fotos"),
]
