import os
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db.models.signals import post_delete
from django.dispatch import receiver
from gerencia.models import SolicitudRelevamiento


class PrecatArchivo(models.Model):
    """
    Modelo para almacenar archivos de Precat subidos por el Digitalizador
    """
    TIPO_PRECAT = 'precat'
    TIPO_PLANOS = 'planos'
    TIPO_CHOICES = [
        (TIPO_PRECAT, 'Archivo Precat (ZIP/RAR/7Z)'),
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
        help_text='Formatos permitidos: .zip, .rar, .7z para Precat; .pdf para Planos'
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
        indexes = [
            models.Index(fields=['solicitud', 'tipo_archivo']),
            models.Index(fields=['subido_por', 'fecha_subida']),
        ]

    def __str__(self):
        return f"{self.get_tipo_archivo_display()} - {self.solicitud.colonia.nombre}"

    def clean(self):
        """Validación del archivo"""
        super().clean()

        if self.archivo:
            # Validar extensión
            filename = self.archivo.name.lower()
            extension = os.path.splitext(filename)[1]

            if self.tipo_archivo == self.TIPO_PRECAT:
                if extension not in ['.zip', '.rar', '.7z']:
                    raise ValidationError({
                        'archivo': 'Los archivos Precat deben ser .zip, .rar o .7z'
                    })
            elif self.tipo_archivo == self.TIPO_PLANOS:
                if extension != '.pdf':
                    raise ValidationError({
                        'archivo': 'Los planos deben ser archivos PDF (.pdf)'
                    })

            # Validar tamaño máximo (50MB)
            max_size = 50 * 1024 * 1024
            if self.archivo.size > max_size:
                raise ValidationError({
                    'archivo': f'El archivo es demasiado grande (máximo 50MB)'
                })

    def save(self, *args, **kwargs):
        """Guardar con validación"""
        self.full_clean()
        super().save(*args, **kwargs)

    def get_nombre_archivo(self):
        """Obtener nombre del archivo sin ruta"""
        return os.path.basename(self.archivo.name)

    def get_tamanio_mb(self):
        """Obtener tamaño en MB"""
        try:
            return round(self.archivo.size / (1024 * 1024), 2)
        except (ValueError, AttributeError):
            return 0

    @property
    def archivo_existe(self):
        """Verifica si el archivo físico existe"""
        try:
            return self.archivo and os.path.exists(self.archivo.path)
        except:
            return False

    @property
    def tipo_icono(self):
        """Devuelve el ícono según el tipo de archivo"""
        if self.tipo_archivo == self.TIPO_PRECAT:
            return 'fas fa-file-archive'
        elif self.tipo_archivo == self.TIPO_PLANOS:
            return 'fas fa-file-pdf'
        return 'fas fa-file'

    def get_url_descarga(self):
        """Genera URL para descargar el archivo"""
        from django.urls import reverse
        return reverse('digitalizador:descargar_precat', args=[self.id])


@receiver(post_delete, sender=PrecatArchivo)
def eliminar_archivo_fisico(sender, instance, **kwargs):
    """Elimina el archivo físico cuando se borra el registro"""
    if instance.archivo and instance.archivo_existe:
        try:
            os.remove(instance.archivo.path)
        except (OSError, FileNotFoundError):
            pass
