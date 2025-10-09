from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Departamento(models.Model):
    nombre = models.CharField(max_length=200, unique=True, db_index=True)
    codigo = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

class Distrito(models.Model):
    nombre = models.CharField(max_length=200)
    departamento = models.ForeignKey(Departamento, on_delete=models.PROTECT, related_name="distritos")

    class Meta:
        unique_together = ("nombre", "departamento")
        verbose_name = "Distrito"
        verbose_name_plural = "Distritos"
        ordering = ["departamento__nombre", "nombre"]

    def clean(self):
        if not self.departamento:
            raise ValidationError("Un distrito debe estar vinculado a un departamento.")

    def __str__(self):
        return f"{self.nombre} ({self.departamento})"
    

class Colonia(models.Model):
    ESTADO_CHOICES = [("activo", "Activo"), ("inactivo", "Inactivo")]
    nombre = models.CharField(max_length=250, db_index=True)
    finca_matriz = models.CharField(max_length=100, blank=True, null=True)
    padron_matriz = models.CharField(max_length=100, blank=True, null=True)
    distritos = models.ManyToManyField(Distrito, related_name="colonias")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="activo")

    class Meta:
        unique_together = ("nombre",)  
        verbose_name = "Colonia"
        verbose_name_plural = "Colonias"
        ordering = ["nombre"]

    def clean(self):
        if self.pk:
            # cuando ya existe, comprobar relación en la DB
            if self.distritos.count() == 0:
                raise ValidationError("La colonia debe estar asociada a al menos un distrito.")
        else:
            # en create: distritos puede venir por form, validación en form
            pass

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # no garantizar aquí la count() para la creación vía admin/form (se valida en forms/admin)

    def __str__(self):
        return self.nombre

class Area(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

class Objetivo(models.Model):
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="objetivos")
    nombre = models.CharField(max_length=250)
    descripcion = models.TextField(blank=True)

    class Meta:
        unique_together = ("area", "nombre")
        verbose_name = "Objetivo"
        verbose_name_plural = "Objetivos"
        ordering = ["area__nombre", "nombre"]

    def clean(self):
        if not self.area:
            raise ValidationError("El objetivo debe estar asociado a un área.")

    def __str__(self):
        return f"{self.nombre} - {self.area.nombre}"

# Solicitud (coordinación)
class Solicitud(models.Model):
    TIPO_CHOICES = [("nuevo", "Nuevo relevamiento"), ("actualizacion", "Actualización de datos")]
    ESTADO_PENDIENTE = "pendiente"
    ESTADO_ACTIVO = "activo"
    ESTADO_EN_PROCESO = "en_proceso"
    ESTADO_INACTIVO = "inactivo"
    ESTADOS = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_ACTIVO, "Activo"),
        (ESTADO_EN_PROCESO, "En proceso de relevamiento"),
        (ESTADO_INACTIVO, "Inactivo"),
    ]

    colonia = models.ForeignKey(Colonia, on_delete=models.CASCADE, related_name="solicitudes")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="nuevo")
    estado = models.CharField(max_length=30, choices=ESTADOS, default=ESTADO_PENDIENTE)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="solicitudes_creadas")
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Solicitud de relevamiento"
        verbose_name_plural = "Solicitudes de relevamiento"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Solicitud #{self.pk} - {self.colonia} ({self.get_estado_display()})"

    def clean(self):
        # Validar existencia de colonia
        if not self.colonia:
            raise ValidationError("La solicitud debe estar vinculada a una colonia.")
        # Evitar duplicados: misma colonia, mismo tipo y estado no inactivo en corto tiempo
        qs = Solicitud.objects.filter(colonia=self.colonia, tipo=self.tipo)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.filter(estado__in=[self.ESTADO_PENDIENTE, self.ESTADO_ACTIVO, self.ESTADO_EN_PROCESO]).exists():
            # Esto previene solicitudes duplicadas activas
            raise ValidationError("Ya existe una solicitud activa o pendiente para esta colonia y tipo.")

    # Control de transiciones; se usará desde vistas con permisos
    def puede_transicionar(self, nuevo_estado):
        allowed = {
            self.ESTADO_PENDIENTE: [self.ESTADO_ACTIVO, self.ESTADO_INACTIVO],
            self.ESTADO_ACTIVO: [self.ESTADO_EN_PROCESO, self.ESTADO_INACTIVO],
            self.ESTADO_EN_PROCESO: [self.ESTADO_ACTIVO, self.ESTADO_INACTIVO],
            self.ESTADO_INACTIVO: [self.ESTADO_ACTIVO],
        }
        return nuevo_estado in allowed.get(self.estado, [])

class SolicitudAudit(models.Model):
    solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, related_name="auditorias")
    previo = models.CharField(max_length=50)
    nuevo = models.CharField(max_length=50)
    cambiado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(default=timezone.now)
    comentario = models.TextField(blank=True)

    class Meta:
        verbose_name = "Audit - Solicitud"
        verbose_name_plural = "Auditorías - Solicitudes"
        ordering = ["-fecha"]

#extraido de core/relevamiento_models.py
class Relevamiento(models.Model):
    colonia = models.ForeignKey(Colonia, on_delete=models.CASCADE, related_name="relevamientos")
    solicitud = models.ForeignKey(Solicitud, on_delete=models.SET_NULL, null=True, blank=True, related_name="relevamientos")
    fecha = models.DateTimeField(default=timezone.now)
    datos = models.JSONField(blank=True, default=dict)  # flexible para los campos relevados
    realizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Relevamiento"
        verbose_name_plural = "Relevamientos"
        ordering = ["-fecha"]
        unique_together = ("colonia", "fecha")  # si requiere unicidad por día/hora ajustar

    def clean(self):
        if self.solicitud and self.solicitud.estado != Solicitud.ESTADO_EN_PROCESO:
            raise ValidationError("La solicitud asociada debe estar en estado 'En proceso de relevamiento'.")
        # evitar duplicados básicos: si ya existe un relevamiento reciente para la misma colonia
        recent = Relevamiento.objects.filter(colonia=self.colonia)
        if self.pk:
            recent = recent.exclude(pk=self.pk)
        # criterio de duplicado: mismo día
        today = timezone.now().date()
        if recent.filter(fecha__date=today).exists():
            raise ValidationError("Ya existe un relevamiento para esta colonia en la fecha de hoy.")
