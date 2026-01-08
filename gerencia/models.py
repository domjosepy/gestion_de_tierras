# gerencia/models.py
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


User = settings.AUTH_USER_MODEL


class SolicitudRelevamiento(models.Model):
    # TIPOS DE SOLICITUD
    TIPO_RELEVAMIENTO = "relevamiento"
    TIPO_ACTUALIZACION = "actualizacion"
    TIPOS = [
        (TIPO_RELEVAMIENTO, "Estudio de Relevamiento"),
        (TIPO_ACTUALIZACION, "Estudio de Actualización"),
    ]

    # ESTADOS DE LA SOLICITUD
    ESTADOS = [
        ("pendiente_asignacion_sig", "Pendiente de Digitalizador"),
        ("asignado_a_digitalizador", "Asignado a Digitalizador"),
        ("en_proceso_digitalizacion", "En Proceso de Digitalización"),
        ("pendiente_revision_sig", "Pendiente de Revisión SIG"),
        ("en_revision_sig", "En Revisión SIG"),
        ("pendiente_asignacion_analista", "Pendiente de Análisis"),
        ("en_analisis", "En Análisis"),
        ("rechazado", "Rechazado"),
        ("aprobado_para_campo", "Aprobado para Campo"),
        ("en_ejecucion_campo", "En Ejecución de Campo"),
    ]

    # Campos principales de la solicitud
    colonia = models.ForeignKey(
        "core.Colonia",
        on_delete=models.PROTECT,
        related_name="solicitudes_relevamiento"
    )
    tipo = models.CharField(max_length=20, choices=TIPOS, editable=False)
    estado = models.CharField(
        max_length=30, choices=ESTADOS, default="pendiente_asignacion_sig")
    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    observaciones = models.TextField(blank=True)
    motivo_rechazo = models.TextField(blank=True)

    # CAMPO DIGITALIZADOR (asignación y fechas)
    digitalizador_asignado = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_como_digitalizador",

    )
    fecha_asignacion_digitalizador = models.DateTimeField(
        null=True, blank=True
    )

    # CAMPO ANALISTA (asignación y fechas)
    analista_asignado = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_como_analista",
    )
    fecha_asignacion_analista = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Solicitud de relevamiento"
        verbose_name_plural = "Solicitudes de relevamiento"
        ordering = ["-fecha_creacion"]

    # MÉTODOS DE VERIFICACIÓN
    def puede_asignar_digitalizador(self):
        return self.estado == "pendiente_asignacion_sig"

    def puede_iniciar_digitalizacion(self):
        return (self.estado == "asignado_a_digitalizador"
                and self.digitalizador_asignado is not None)

    def puede_finalizar_digitalizacion(self):
        return (self.estado == "en_proceso_digitalizacion"
                and self.digitalizador_asignado is not None)

    def puede_asignar_analista(self):
        return self.estado == "pendiente_asignacion_analista"

    # Estados editables por cada rol
    @property
    def estados_editables_sig(self):
        return ["pendiente_asignacion_sig", "asignado_a_digitalizador",
                "en_proceso_digitalizacion", "pendiente_revision_sig"]

    @property
    def estados_editables_digitalizador(self):
        return ["asignado_a_digitalizador", "en_proceso_digitalizacion"]

    @property
    def estados_editables_analista(self):
        return ["pendiente_asignacion_analista", "en_analisis"]

    def save(self, *args, **kwargs):
        es_nuevo = not self.pk

        if es_nuevo:
            # Definir tipo automáticamente al crear
            if self.colonia and hasattr(self.colonia, "tiene_relevamiento"):
                if self.colonia.tiene_relevamiento:
                    self.tipo = self.TIPO_ACTUALIZACION
                    self.estado = "pendiente_asignacion_analista"
                else:
                    self.tipo = self.TIPO_RELEVAMIENTO
                    self.estado = "pendiente_asignacion_sig"
        else:
            # Para registros existentes
            try:
                original = SolicitudRelevamiento.objects.get(pk=self.pk)

                # Registrar asignación de digitalizador
                if (original.digitalizador_asignado != self.digitalizador_asignado
                        and self.digitalizador_asignado is not None):
                    self.fecha_asignacion_digitalizador = timezone.now()
                    if self.estado == "pendiente_asignacion_sig":
                        self.estado = "asignado_a_digitalizador"

                # Registrar asignación de analista
                if (original.analista_asignado != self.analista_asignado
                        and self.analista_asignado is not None):
                    self.fecha_asignacion_analista = timezone.now()
                    if self.estado == "pendiente_asignacion_analista":
                        self.estado = "en_analisis"

            except SolicitudRelevamiento.DoesNotExist:
                pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Solicitud {self.pk} - {self.colonia} ({self.get_estado_display()})"


class SolicitudRelevamientoAudit(models.Model):
    solicitud = models.ForeignKey(
        SolicitudRelevamiento, on_delete=models.CASCADE, related_name="auditorias")
    previo = models.CharField(max_length=50)
    nuevo = models.CharField(max_length=50)
    cambiado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(blank=True)

    class Meta:
        verbose_name = "Auditoría - Solicitud Relevamiento"
        verbose_name_plural = "Auditorías - Solicitudes Relevamiento"
        ordering = ["-fecha"]
