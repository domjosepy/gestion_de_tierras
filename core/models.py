from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

User = settings.AUTH_USER_MODEL

# ===============================
# MODELO: DEPARTAMENTO
# ===============================


class Departamento(models.Model):
    nombre = models.CharField(max_length=200, unique=True, db_index=True)
    codigo = models.PositiveIntegerField(blank=True, null=True, unique=True)

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ["codigo", "nombre"]

    def save(self, *args, **kwargs):
        if not self.codigo:
            # Obtener los códigos existentes
            codigos_existentes = list(
                self.__class__.objects.exclude(codigo__isnull=True)
                .values_list("codigo", flat=True)
            )

            # Buscar el primer número libre
            nuevo_codigo = 1
            while nuevo_codigo in codigos_existentes:
                nuevo_codigo += 1

            self.codigo = nuevo_codigo

        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


# ===============================
# MODELO: DISTRITO
# ===============================
class Distrito(models.Model):
    nombre = models.CharField(max_length=200)
    departamento = models.ForeignKey(
        Departamento, on_delete=models.PROTECT, related_name="distritos"
    )
    # No es único globalmente !!antes unique=True
    codigo = models.PositiveIntegerField(blank=True, null=True, unique=False)

    class Meta:
        unique_together = ("nombre", "departamento")
        unique_together = ("codigo", "departamento")
        verbose_name = "Distrito"
        verbose_name_plural = "Distritos"
        ordering = ["departamento__nombre", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.departamento.nombre})"


# ===============================
# MODELO: COLONIA
# ===============================
class Colonia(models.Model):
    ESTADO_CHOICES = [("activo", "Activo"), ("inactivo", "Inactivo")]

    nombre = models.CharField(max_length=250, db_index=True)
    finca_matriz = models.CharField(max_length=100, blank=True, null=True)
    padron_matriz = models.CharField(max_length=100, blank=True, null=True)
    distritos = models.ManyToManyField(Distrito, related_name="colonias")
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default="activo")
    codigo = models.PositiveIntegerField(blank=True, null=True)

    tiene_relevamiento = models.BooleanField(
        default=False,
        verbose_name="¿Tiene relevamiento previo?"
    )

    class Meta:
        verbose_name = "Colonia"
        verbose_name_plural = "Colonias"
        ordering = ["nombre"]

    def save(self, *args, **kwargs):
        if not self.codigo:
            codigos_existentes = list(
                self.__class__.objects.exclude(codigo__isnull=True)
                .values_list("codigo", flat=True)
            )
            nuevo_codigo = 1
            while nuevo_codigo in codigos_existentes:
                nuevo_codigo += 1
            self.codigo = nuevo_codigo
        super().save(*args, **kwargs)

    def departamentos_unicos(self):
        """
        Retorna los departamentos únicos asociados a los distritos de la colonia
        """
        departamentos = []
        departamentos_vistos = set()

        for distrito in self.distritos.all():
            depto = distrito.departamento
            if depto.id not in departamentos_vistos:
                departamentos_vistos.add(depto.id)
                departamentos.append(depto)

        return departamentos

    def clean(self):
        if self.pk:
            if self.distritos.count() == 0:
                raise ValidationError(
                    "La colonia debe estar asociada a al menos un distrito."
                )

    def __str__(self):
        return self.nombre
