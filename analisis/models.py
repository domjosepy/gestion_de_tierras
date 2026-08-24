from django.db import models
from django.conf import settings


class AsignacionAnalista(models.Model):
    """
    Registro auditable de cada asignación de un relevamiento a un analista.
    Cada cambio de analista genera una nueva fila (cancelando la anterior),
    garantizando historial completo.
    """
    ESTADOS = [
        ('analista_asignado', 'Asignado'),
        ('proceso_analisis', 'En Proceso'),
        ('proceso_empate', 'En Proceso de Empate'),
        ('analisis_finalizado', 'Finalizado'),
        ('analisis_cancelado', 'Cancelado'),
    ]

    solicitud = models.ForeignKey(
        'gerencia.SolicitudRelevamiento',
        on_delete=models.CASCADE,
        related_name='asignaciones_analista',
        verbose_name='Solicitud',
    )
    orden_trabajo = models.ForeignKey(
        'coordinacion.OrdenTrabajo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asignaciones_analista',
        verbose_name='Orden de Trabajo analizada',
    )
    analista = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asignaciones_analista_recibidas',
        verbose_name='Analista',
    )
    lider_asignador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asignaciones_analista_realizadas',
        verbose_name='Líder asignador',
    )
    fecha_asignacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de asignación',
    )
    fecha_termino = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de término',
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='analista_asignado',
        verbose_name='Estado',
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones',
    )

    class Meta:
        verbose_name = 'Asignación de Análisis'
        verbose_name_plural = 'Asignaciones de Análisis'
        ordering = ['-fecha_asignacion']

    def __str__(self):
        analista = self.analista.username if self.analista else 'sin-analista'
        colonia = self.solicitud.colonia if self.solicitud_id else '?'
        return f"Asignación {self.pk} - {colonia} → {analista} [{self.estado}]"

