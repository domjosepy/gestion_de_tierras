from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings
from django.utils import timezone


class Rol(models.Model):
    """
    Modelo independiente para roles con permisos personalizables.
    Incluye relación bidireccional con grupos de Django.
    """
    nombre = models.CharField(
        max_length=50, unique=True, verbose_name='Nombre del Rol')
    descripcion = models.TextField(blank=True)
    permisos = models.ManyToManyField(
        Permission,
        blank=True,
        verbose_name='Permisos asociados',
        help_text='Selecciona permisos específicos para este rol'
    )
    grupo_django = models.OneToOneField(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Grupo de Django asociado',
        help_text='Grupo de Django sincronizado con este rol'
    )
    color = models.CharField(
        max_length=20,
        default='#6c757d',
        help_text='Color en formato hexadecimal (ej: #007bff)'
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        # Crear/actualizar grupo de Django cuando se guarda el rol
        if not self.grupo_django:
            grupo, created = Group.objects.get_or_create(
                name=f"Rol_{self.nombre}")
            self.grupo_django = grupo
        else:
            self.grupo_django.name = f"Rol_{self.nombre}"
            self.grupo_django.save()

        super().save(*args, **kwargs)

    def sincronizar_permisos(self):
        """Sincroniza permisos del rol con el grupo de Django"""
        if self.grupo_django:
            self.grupo_django.permissions.clear()
            self.grupo_django.permissions.add(*self.permisos.all())


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

    fecha_aprobacion = models.DateTimeField(
        null=True, blank=True, verbose_name='Fecha de aprobación')
    aprobado_por = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios_aprobados',
        verbose_name='Aprobado por'
    )

    # Propiedad para obtener permisos combinados

    @property
    def permisos_combinados(self):
        """Devuelve todos los permisos del usuario (directos + rol + grupos)"""
        permisos = set()

        # Permisos directos del usuario
        permisos.update(self.user_permissions.all())

        # Permisos del rol
        if self.rol and self.rol.permisos.exists():
            permisos.update(self.rol.permisos.all())

        # Permisos de grupos de Django
        permisos.update(Permission.objects.filter(group__user=self))

        return permisos

    def tiene_permiso(self, permiso_codename):
        """Verifica si usuario tiene un permiso específico"""
        return any(p.codename == permiso_codename for p in self.permisos_combinados)


class Grupo(models.Model):
    """
    Modelo para grupos organizacionales (no para permisos).
    Ej: 'Marketing', 'Desarrollo', 'Soporte Técnico'
    """
    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre del Grupo'
    )

    descripcion = models.TextField(
        blank=True,
        verbose_name='Descripción',
        help_text='Propósito u objetivo del grupo'
    )

    # Relación con usuarios (muchos a muchos)
    usuarios = models.ManyToManyField(
        User,
        related_name='grupos_pertenece',
        blank=True,
        verbose_name='Usuarios en el grupo',
        help_text='Selecciona los usuarios que pertenecen a este grupo'
    )

    # Relación con roles (opcional pero útil)
    roles_asociados = models.ManyToManyField(
        Rol,
        related_name='grupos_asociados',
        blank=True,
        verbose_name='Roles comúnmente asignados',
        help_text='Roles que suelen tener los usuarios de este grupo'
    )

    lider = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grupos_liderados',
        verbose_name='Líder del grupo',
        help_text='Usuario responsable del grupo'
    )

    color = models.CharField(
        max_length=20,
        default='#6c757d',
        help_text='Color identificativo (formato hexadecimal)'
    )

    es_departamento = models.BooleanField(
        default=False,
        verbose_name='¿Es departamento?',
        help_text='Marcar si representa un departamento organizacional'
    )

    activo = models.BooleanField(
        default=True,
        verbose_name='Activo'
    )

    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grupos_creados',
        verbose_name='Creado por'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Grupo'
        verbose_name_plural = 'Grupos'
        ordering = ['nombre']
        permissions = [
            ("gestionar_grupos", "Puede gestionar grupos y asignaciones"),
        ]

    def __str__(self):
        return self.nombre

    @property
    def cantidad_usuarios(self):
        """Retorna la cantidad de usuarios en el grupo"""
        return self.usuarios.count()

    @property
    def cantidad_roles_asociados(self):
        """Retorna la cantidad de roles asociados"""
        return self.roles_asociados.count()

    def get_usuarios_activos(self):
        """Retorna solo los usuarios activos del grupo"""
        return self.usuarios.filter(estado='ACTIVO', is_active=True)

    def save(self, *args, **kwargs):
        # Si no se especifica quién creó el grupo, usar el usuario actual
        if not self.creado_por and hasattr(self, '_current_user'):
            self.creado_por = self._current_user
        super().save(*args, **kwargs)


class FlujoTrabajo(models.Model):
    """Define qué grupo maneja cada estado del flujo"""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)

    # Estados y sus grupos asignados
    grupo_sig = models.ForeignKey(
        'Grupo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flujos_sig',
        verbose_name='Grupo para SIG'
    )

    grupo_analisis = models.ForeignKey(
        'Grupo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flujos_analisis',
        verbose_name='Grupo para Análisis'
    )

    grupo_monitoreo = models.ForeignKey(
        'Grupo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flujos_monitoreo',
        verbose_name='Grupo para Monitoreo'
    )

    grupo_campo = models.ForeignKey(
        'Grupo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flujos_campo',
        verbose_name='Grupo para Campo'
    )

    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Flujo de Trabajo'
        verbose_name_plural = 'Flujos de Trabajo'

    def __str__(self):
        return self.nombre

    def obtener_grupo_por_estado(self, estado):
        """Devuelve el grupo correspondiente a un estado"""
        if 'sig' in estado:
            return self.grupo_sig
        elif 'analista' in estado or 'analisis' in estado:
            return self.grupo_analisis
        elif 'aprobado' in estado:
            return self.grupo_monitoreo
        elif 'campo' in estado:
            return self.grupo_campo
        return None
