from django.db import models
from django.conf import settings


# Registro de asignaciones al digitalizador
class AsignacionDigitalizador(models.Model):
	solicitud = models.ForeignKey(
		'gerencia.SolicitudRelevamiento',
		on_delete=models.CASCADE,
		related_name='asignaciones_digitalizador',
		verbose_name='Solicitud'
	)
	registrado_por = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='asignaciones_registradas',
		verbose_name='Registrado por'
	)
	usuario_asignado = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='asignaciones_recibidas',
		verbose_name='Usuario asignado'
	)
	fecha_asignacion = models.DateTimeField(
		auto_now_add=True,
		verbose_name='Fecha de asignación'
	)

	class Meta:
		verbose_name = 'Asignación a digitalizador'
		verbose_name_plural = 'Asignaciones a digitalizador'
		ordering = ['-fecha_asignacion']

	def __str__(self):
		user = self.usuario_asignado.username if self.usuario_asignado else 'sin-usuario'
		return f"Asignación {self.pk} - Solicitud {self.solicitud_id} -> {user}"

