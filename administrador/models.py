from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.core.validators import RegexValidator

class Rol(models.Model):
    """
    Modelo independiente para roles con permisos personalizables.
    """
    nombre = models.CharField(max_length=50, unique=True, verbose_name='Nombre del Rol')
    descripcion = models.TextField(blank=True)
    permisos = models.ManyToManyField(
        Permission,
        blank=True,
        verbose_name='Permisos asociados',
        help_text='Selecciona permisos específicos para este rol'
    )
    color = models.CharField(
        max_length=20,
        default='secondary', 
        help_text='Color para representar el rol (ej: primary, danger)'
    )

    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class User(AbstractUser):
    CREADO_POR_CHOICES = (
        ('usuario', 'Usuario'),
        ('admin', 'Administrador'),
    )

    creado_por = models.CharField(
        max_length=20,
        choices=CREADO_POR_CHOICES,
        default='usuario',
        verbose_name='Creado por'
    )
    """
    Usuario personalizado con relación a Rol (FK).
    """
    ESTADOS = (
        ('PENDIENTE', 'Pendiente de aprobación'),
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
    )
    
    ci = models.CharField(
        max_length=8,
        blank=True,
        null=True,
        validators=[RegexValidator(
            regex='^[0-9]{7,8}$',
            message='La cédula debe tener 7 u 8 dígitos numéricos.'
        )],
        verbose_name='Cédula de Identidad'
    )
    rol = models.ForeignKey(
        Rol,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Rol asignado'
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='PENDIENTE',
        verbose_name='Estado de cuenta'
    )
    telefono = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        validators=[RegexValidator(
            regex='^[0-9]{10}$',
            message='El teléfono debe tener 10 dígitos numéricos.'
        )]
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("asignar_roles", "Puede asignar roles a usuarios"),
            ("aprobar_usuarios", "Puede aprobar usuarios pendientes"),
        ]

    # Solución para los conflictos con Group/Permission
    groups = models.ManyToManyField(
        Group,
        verbose_name='grupos',
        blank=True,
        help_text='Los grupos a los que pertenece este usuario.',
        related_name="custom_user_groups",
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='permisos de usuario',
        blank=True,
        help_text='Los permisos específicos de este usuario.',
        related_name="custom_user_permissions",
        related_query_name="custom_user",
    )

    @property
    def rol_efectivo(self):
        """
        Devuelve siempre un objeto con atributos de Rol.
        Si es superuser, crea un 'rol falso' llamado Administrador.
        """
        if self.is_superuser:
            return type('RolFake', (), {
                'nombre': 'administrador',
                'color': 'danger'
            })()
        return self.rol

    @property
    def rol_nombre(self):
        """
        Devuelve el nombre del rol efectivo.
        """
        return self.rol_efectivo.nombre if self.rol_efectivo else "Sin rol"

    def get_rol_color(self):
        return self.rol_efectivo.color if self.rol_efectivo else 'light'

    def __str__(self):
        return f"{self.username} ({self.get_estado_display()})"
