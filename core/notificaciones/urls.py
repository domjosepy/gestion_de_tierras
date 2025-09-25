from django.urls import path
from . import views

app_name = "notificaciones"

urlpatterns = [
    path("marcar-todas-leidas/", views.marcar_todas_leidas, name="marcar_todas_leidas"),
]
