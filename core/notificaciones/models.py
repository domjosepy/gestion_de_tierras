from django.db import models
from administrador.models import User  # Importa tu User personalizado

class Notificacion(models.Model):
    TIPOS = (
        ('USUARIO_NUEVO', 'Nuevo usuario registrado'),
        ('USUARIO_APROBADO', 'Usuario aprobado'),
        ('ALERTA', 'Alerta del sistema'),
    )
    
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )
    mensaje = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPOS, default='ALERTA')
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(blank=True, null=True)  # Datos adicionales

    class Meta:
        ordering = ['-fecha']
        verbose_name_plural = 'Notificaciones'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.usuario.username}"

    @classmethod
    def notificar_nuevo_usuario(cls, usuario_nuevo):
        admins = User.objects.filter(is_superuser=True)
        mensaje = f"Nuevo usuario registrado: {usuario_nuevo.username}"
        
        for admin in admins:
            cls.objects.create(
                usuario=admin,
                mensaje=mensaje,
                tipo='USUARIO_NUEVO',
                metadata={
                    'user_id': usuario_nuevo.id,
                    'fecha_registro': usuario_nuevo.date_joined.isoformat()
                }
            )