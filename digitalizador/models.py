from django.db import models
from django.conf import settings
from gerencia.models import SolicitudRelevamiento


class PrecatArchivo(models.Model):
    """
    Modelo para almacenar archivos de Precat subidos por el Digitalizador
    """
    TIPO_PRECAT = 'precat'
    TIPO_PLANOS = 'planos'
    TIPO_CHOICES = [
        (TIPO_PRECAT, 'Archivo Precat (ZIP/RAR)'),
        (TIPO_PLANOS, 'Planos de Referencia (PDF)'),
    ]

    solicitud = models.ForeignKey(
        SolicitudRelevamiento,
        on_delete=models.CASCADE,
        related_name='precat_archivos',
        verbose_name='Solicitud de Relevamiento'
    )
    tipo_archivo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        verbose_name='Tipo de Archivo'
    )
    archivo = models.FileField(
        upload_to='precat/%Y/%m/%d/',
        verbose_name='Archivo',
        help_text='Formatos permitidos: .zip, .rar para Precat; .pdf para Planos'
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones del Digitalizador'
    )
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='precat_subidos',
        verbose_name='Subido por'
    )
    fecha_subida = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Subida'
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Modificación'
    )

    class Meta:
        verbose_name = 'Archivo de Precat'
        verbose_name_plural = 'Archivos de Precat'
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"{self.get_tipo_archivo_display()} - {self.solicitud.colonia.nombre}"

    def get_nombre_archivo(self):
        """Obtener nombre del archivo sin ruta"""
        return self.archivo.name.split('/')[-1]

    def get_tamanio_mb(self):
        """Obtener tamaño en MB"""
        try:
            return round(self.archivo.size / (1024 * 1024), 2)
        except (ValueError, AttributeError):
            return 0
