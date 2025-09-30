from django.db import models
from django.conf import settings

class Notificacion(models.Model):
    TIPOS = (
        ("INFO", "Información"),
        ("WARNING", "Advertencia"),
        ("SUCCESS", "Éxito"),
        ("ERROR", "Error"),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificaciones"
    )
    mensaje = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS, default="INFO")
    leida = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    
    link = models.CharField(max_length=255, blank=True, null=True)


    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.tipo} - {self.mensaje[:30]}"
