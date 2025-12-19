# gerencia/models.py
from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class SolicitudRelevamiento(models.Model):
    # Tipos de solicitud según colonia
    TIPO_RELEVAMIENTO = "relevamiento"
    TIPO_ACTUALIZACION = "actualizacion"
    TIPOS = [
        (TIPO_RELEVAMIENTO, "Estudio de Relevamiento"),
        (TIPO_ACTUALIZACION, "Estudio de Actualización"),
    ]

    # Estados del workflow
    ESTADOS = [
        ("pendiente_asignacion_sig", "Pendiente de Digitalizador"),
        ("asignado_a_digitalizador", "Asignado a Digitalizador"),
        ("en_proceso_digitalizacion", "En Proceso de Digitalización"),
        ("pendiente_asignacion_analista", "Pendiente de Análisis"),
        ("en_analisis", "En Análisis"),
        ("rechazado", "Rechazado"),
        ("aprobado_para_campo", "Aprobado para Campo"),
        ("en_ejecucion_campo", "En Ejecución de Campo"),
    ]

    colonia = models.ForeignKey(
        "core.Colonia",
        on_delete=models.PROTECT,
        related_name="solicitudes_relevamiento"
    )
    tipo = models.CharField(max_length=20, choices=TIPOS)
    estado = models.CharField(max_length=30, choices=ESTADOS, default="pendiente_asignacion_sig")
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    observaciones = models.TextField(blank=True)
    motivo_rechazo = models.TextField(blank=True)

    class Meta:
        verbose_name = "Solicitud de relevamiento"
        verbose_name_plural = "Solicitudes de relevamiento"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Solicitud {self.pk} - {self.colonia} ({self.get_estado_display()})"


class SolicitudRelevamientoAudit(models.Model):
    solicitud = models.ForeignKey(SolicitudRelevamiento, on_delete=models.CASCADE, related_name="auditorias")
    previo = models.CharField(max_length=50)
    nuevo = models.CharField(max_length=50)
    cambiado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(blank=True)

    class Meta:
        verbose_name = "Auditoría - Solicitud Relevamiento"
        verbose_name_plural = "Auditorías - Solicitudes Relevamiento"
        ordering = ["-fecha"]
