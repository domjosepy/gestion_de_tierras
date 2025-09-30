from django.urls import path
from . import views

app_name = "notificaciones"

urlpatterns = [
    path("lista/", views.lista_notificaciones, name="lista"),
    path("marcar-todas-leidas/", views.marcar_todas_leidas, name="marcar_todas_leidas"),
    path("eliminar/<int:pk>/", views.eliminar_notificacion, name="eliminar"),
    path("eliminar-seleccionadas/", views.eliminar_seleccionadas, name="eliminar_seleccionadas"),
    path("eliminar-todas/", views.eliminar_todas, name="eliminar_todas"),
]
