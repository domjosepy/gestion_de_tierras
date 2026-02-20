from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

User = settings.AUTH_USER_MODEL


class EquipoRelevamiento(models.Model):
    """
    Modelo para equipos de relevamiento que se asignan a las órdenes de trabajo
    """
    ESTADOS_EQUIPO = [
        ('planificado', 'Planificado'),
        ('en_campo', 'En Campo'),
        ('pausado', 'Pausado'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]

    TIPOS_EQUIPO = [
        ('completo', 'Equipo Completo'),
        ('rapido', 'Equipo Rápido'),
        ('especial', 'Equipo Especial'),
    ]

    nombre = models.CharField(max_length=100, verbose_name="Nombre del equipo")
    tipo = models.CharField(
        max_length=20, choices=TIPOS_EQUIPO, default='completo')
    estado = models.CharField(
        max_length=20, choices=ESTADOS_EQUIPO, default='planificado')

    # Liderazgo del equipo
    coordinador_campo = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='equipos_coordinados',
        verbose_name="Coordinador de Campo"
    )
    subcoordinadores = models.ManyToManyField(
        User,
        related_name='equipos_subcoordinados',
        verbose_name="Subcoordinadores",
        blank=True
    )

    # Miembros del equipo
    encuestadores = models.ManyToManyField(
        User,
        related_name='equipos_encuestador',
        verbose_name="Encuestadores",
        blank=True
    )
    choferes = models.ManyToManyField(
        User,
        related_name='equipos_chofer',
        verbose_name="Choferes",
        blank=True
    )

    # Recursos
    vehiculos = models.TextField(
        blank=True, verbose_name="Vehículos asignados")
    equipos = models.TextField(blank=True, verbose_name="Equipos y materiales")

    # Configuración
    max_encuestadores = models.IntegerField(
        default=4, verbose_name="Máximo de encuestadores")
    activo = models.BooleanField(default=True, verbose_name="Equipo activo")

    # Fechas
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Equipo de Relevamiento"
        verbose_name_plural = "Equipos de Relevamiento"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} - {self.get_estado_display()}"

    @property
    def total_miembros(self):
        """Retorna el total de miembros en el equipo"""
        total = 1  # coordinador_campo
        total += self.subcoordinadores.count()
        total += self.encuestadores.count()
        total += self.choferes.count()
        return total

    @property
    def disponible(self):
        """Verifica si el equipo está disponible para asignar"""
        return self.activo and self.estado in ['planificado']


class OrdenTrabajo(models.Model):
    """
    Modelo para órdenes de trabajo generadas desde las solicitudes
    """
    ESTADOS_ORDEN = [
        ('generada', 'Generada'),
        ('asignada', 'Asignada a Equipos'),
        ('en_proceso', 'En Proceso'),
        ('pausada', 'Pausada'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]

    PRIORIDADES = [
        ('critica', 'Crítica'),
        ('alta', 'Alta'),
        ('media', 'Media'),
        ('baja', 'Baja'),
    ]

    # Relación con la solicitud
    solicitud = models.OneToOneField(
        'gerencia.SolicitudRelevamiento',
        on_delete=models.CASCADE,
        related_name='orden_trabajo',
        verbose_name="Solicitud de origen"
    )

    # Información de la orden
    numero_orden = models.CharField(
        max_length=50, unique=True, verbose_name="Número de Orden")
    estado = models.CharField(
        max_length=20, choices=ESTADOS_ORDEN, default='generada')
    prioridad = models.CharField(
        max_length=20, choices=PRIORIDADES, default='media')

    # Asignaciones
    equipos_asignados = models.ManyToManyField(
        EquipoRelevamiento,
        related_name='ordenes_trabajo',
        verbose_name="Equipos asignados",
        blank=True
    )

    # Responsables
    coordinador_responsable = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ordenes_coordinadas',
        verbose_name="Coordinador Responsable"
    )

    # Planificación
    fecha_inicio_planeada = models.DateField(
        verbose_name="Fecha de inicio planeada")
    fecha_fin_planeada = models.DateField(verbose_name="Fecha de fin planeada")
    fecha_inicio_real = models.DateField(
        null=True, blank=True, verbose_name="Fecha de inicio real")
    fecha_fin_real = models.DateField(
        null=True, blank=True, verbose_name="Fecha de fin real")

    # Metas y objetivos
    meta_encuestas = models.IntegerField(
        default=0, verbose_name="Meta de encuestas")
    encuestas_completadas = models.IntegerField(
        default=0, verbose_name="Encuestas completadas")

    # Información adicional
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    instrucciones_especiales = models.TextField(
        blank=True, verbose_name="Instrucciones especiales")

    # Seguimiento
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ordenes_creadas',
        verbose_name="Creado por"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Orden de Trabajo"
        verbose_name_plural = "Órdenes de Trabajo"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"OT-{self.numero_orden} - {self.solicitud.colonia.nombre}"

    def clean(self):
        """Validaciones"""
        if self.fecha_inicio_planeada and self.fecha_fin_planeada:
            if self.fecha_inicio_planeada > self.fecha_fin_planeada:
                raise ValidationError(
                    "La fecha de fin debe ser posterior a la fecha de inicio")

    def save(self, *args, **kwargs):
        """Generar número de orden automáticamente si no existe"""
        if not self.numero_orden:
            self.numero_orden = self.generar_numero_orden()

        # Si se está completando, actualizar fechas
        if self.estado == 'completada' and not self.fecha_fin_real:
            self.fecha_fin_real = timezone.now().date()

        super().save(*args, **kwargs)

    def generar_numero_orden(self):
        """Genera un número de orden único"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        return f"OT-{timestamp}-{self.solicitud_id}"

    @property
    def progreso(self):
        """Calcula el progreso de las encuestas"""
        if self.meta_encuestas > 0:
            return (self.encuestas_completadas / self.meta_encuestas) * 100
        return 0

    @property
    def atrasada(self):
        """Verifica si la orden está atrasada"""
        if self.estado in ['generada', 'asignada', 'en_proceso']:
            if self.fecha_fin_planeada < timezone.now().date():
                return True
        return False

    @property
    def duracion_planeada(self):
        """Calcula la duración planeada en días"""
        if self.fecha_inicio_planeada and self.fecha_fin_planeada:
            return (self.fecha_fin_planeada - self.fecha_inicio_planeada).days
        return 0


class RegistroCampo(models.Model):
    """
    Registro diario de actividades en campo
    """
    TIPOS_REGISTRO = [
        ('inicio', 'Inicio de Jornada'),
        ('actividad', 'Actividad Normal'),
        ('problema', 'Problema/Incidente'),
        ('cierre', 'Cierre de Jornada'),
    ]

    orden_trabajo = models.ForeignKey(
        OrdenTrabajo,
        on_delete=models.CASCADE,
        related_name='registros_campo'
    )
    equipo = models.ForeignKey(
        EquipoRelevamiento,
        on_delete=models.CASCADE,
        related_name='registros_campo'
    )
    tipo = models.CharField(max_length=20, choices=TIPOS_REGISTRO)

    # Ubicación
    latitud = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)
    ubicacion_texto = models.CharField(max_length=255, blank=True)

    # Actividades
    actividades_realizadas = models.TextField(
        verbose_name="Actividades realizadas")
    encuestas_completadas = models.IntegerField(default=0)
    problemas_encontrados = models.TextField(blank=True)

    # Tiempos
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField(null=True, blank=True)
    fecha_registro = models.DateField(default=timezone.now)

    # Firmas
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='registros_campo'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de Campo"
        verbose_name_plural = "Registros de Campo"
        ordering = ['-fecha_registro', '-hora_inicio']

    def __str__(self):
        return f"Registro {self.fecha_registro} - {self.equipo.nombre}"


class Monitoreo(models.Model):
    """
    Sistema de monitoreo en tiempo real
    """
    orden_trabajo = models.ForeignKey(
        OrdenTrabajo,
        on_delete=models.CASCADE,
        related_name='monitoreos'
    )
    equipo = models.ForeignKey(
        EquipoRelevamiento,
        on_delete=models.CASCADE,
        related_name='monitoreos'
    )

    # Ubicación actual
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    precision = models.FloatField(
        null=True, blank=True, help_text="Precisión en metros")

    # Estado actual
    estado_actual = models.CharField(
        max_length=50, verbose_name="Estado actual")
    bateria_dispositivo = models.IntegerField(
        null=True, blank=True, verbose_name="Batería (%)")
    senal_celular = models.IntegerField(
        null=True, blank=True, verbose_name="Señal celular")

    # Timestamp
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Punto de Monitoreo"
        verbose_name_plural = "Puntos de Monitoreo"
        ordering = ['-timestamp']

    def __str__(self):
        return f"Monitoreo {self.equipo.nombre} - {self.timestamp.strftime('%H:%M')}"
