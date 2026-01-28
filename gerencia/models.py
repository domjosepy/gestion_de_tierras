from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from administrador.models import Grupo, FlujoTrabajo
from django.db.models import Q
from core.models import Colonia
from django.db.models import Avg, F, ExpressionWrapper, DurationField

User = settings.AUTH_USER_MODEL


class SolicitudRelevamiento(models.Model):
    TIPO_RELEVAMIENTO = "relevamiento"
    TIPO_ACTUALIZACION = "actualizacion"
    TIPOS = [
        (TIPO_RELEVAMIENTO, "Estudio de Relevamiento"),
        (TIPO_ACTUALIZACION, "Estudio de Actualización")
    ]

    PRIORIDADES = [
        ("alta", "Alta"),
        ("media", "Media"),
        ("baja", "Baja"),
    ]

    ESTADOS = [
        ("pendiente_asignacion_sig", "Pendiente de Asignación SIG"),
        ("asignado_a_digitalizador", "Asignado a Digitalizador"),
        ("en_proceso_digitalizacion", "En Proceso de Digitalización"),
        ("pendiente_revision_sig", "Pendiente de Revisión SIG"),
        ("pendiente_asignacion_analista", "Pendiente de Asignación Análisis"),
        ("pendiente_revision_analista", "Pendiente de Revisión Análisis"),
        ("en_proceso_analisis", "En Proceso de Análisis"),
        ("rechazado", "Rechazado"),
        ("pendiente_aprobacion_campo", "Pendiente Aprobación para Campo"),
        ("aprobado_para_campo", "Aprobado para Campo"),
        ("asignado_coordinacion", "Asignado a Coordinación"),
        ("preparacion_campo", "En Preparación de Campo"),
        ("en_ejecucion_campo", "En Ejecución de Campo"),
        ("pendiente_cierre", "Pendiente de Cierre"),
        ("finalizado", "Finalizado"),
    ]

    # Mapeo de estados a grupos (para lógica de asignación automática)
    GRUPOS_POR_ESTADO = {
        # Estados SIG
        "pendiente_asignacion_sig": ["SIG"],
        "asignado_a_digitalizador": ["SIG"],
        "en_proceso_digitalizacion": ["SIG"],
        "pendiente_revision_sig": ["SIG"],

        # Estados Análisis
        "pendiente_asignacion_analista": ["ANALISIS"],
        "asignado_a_analista": ["ANALISIS"],
        "en_proceso_analisis": ["ANALISIS"],

        # Estado de aprobación campo (dinámico por tipo)
        "pendiente_aprobacion_campo": {
            "relevamiento": ["SIG"],           # Para nuevos: SIG aprueba
            # Para actualizaciones: Análisis aprueba
            "actualizacion": ["ANALISIS"]
        },

        # Estados Coordinación y Monitoreo
        "aprobado_para_campo": ["COORDINACION Y MONITOREO", "COORDINACION", "MONITOREO"],
        "asignado_coordinacion": ["COORDINACION Y MONITOREO", "COORDINACION", "MONITOREO"],
        "preparacion_campo": ["COORDINACION Y MONITOREO", "COORDINACION", "MONITOREO"],
        "en_ejecucion_campo": ["COORDINACION Y MONITOREO", "COORDINACION", "MONITOREO"],
        "pendiente_cierre": ["COORDINACION Y MONITOREO", "COORDINACION", "MONITOREO"],

        # Estados finales (sin grupo)
        "rechazado": [],
        "finalizado": [],
    }

    # CAMPOS PRINCIPALES
    colonia = models.ForeignKey(
        "core.Colonia",
        on_delete=models.PROTECT,
        related_name="solicitudes_relevamiento",
        verbose_name="Colonia"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPOS,
        editable=False,
        verbose_name="Tipo de estudio"
    )

    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDADES,
        default="baja",
        verbose_name="Prioridad"
    )
    estado = models.CharField(
        max_length=30,
        choices=ESTADOS,
        verbose_name="Estado"
    )
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_creadas",
        verbose_name="Creado por"
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación"
    )
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Última modificación"
    )
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones"
    )
    motivo_rechazo = models.TextField(
        blank=True,
        verbose_name="Motivo de rechazo"
    )

    # ASIGNACIÓN DINÁMICA
    grupo_asignado = models.ForeignKey(
        Grupo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_actuales",
        verbose_name="Grupo asignado"
    )
    usuario_asignado = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tareas_asignadas",
        verbose_name="Usuario asignado"
    )
    asignado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asignaciones_realizadas",
        verbose_name="Asignado por"
    )
    fecha_asignacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de asignación"
    )

    # CONTROL DE TIEMPOS
    fecha_inicio_etapa = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Inicio de etapa actual"
    )
    tiempo_digitalizacion = models.DurationField(
        null=True,
        blank=True,
        verbose_name="Tiempo total SIG"
    )
    tiempo_analisis = models.DurationField(
        null=True,
        blank=True,
        verbose_name="Tiempo total Análisis"
    )
    tiempo_campo = models.DurationField(
        null=True,
        blank=True,
        verbose_name="Tiempo total Campo"
    )
    tiempo_total = models.DurationField(
        null=True,
        blank=True,
        verbose_name="Tiempo total proceso"
    )

    # FECHAS ESPECÍFICAS
    fecha_aprobacion_campo = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de aprobación para campo"
    )
    fecha_inicio_campo = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de inicio de campo"
    )
    fecha_fin_campo = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de fin de campo"
    )
    fecha_finalizacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de finalización"
    )
    # Agrega estos métodos a la clase SolicitudRelevamiento (al final de la clase, antes de la clase Meta)

    @classmethod
    def obtener_estadisticas(cls):
        """Obtener estadísticas generales de solicitudes"""
        total = cls.objects.count()
        rechazadas = cls.objects.filter(estado="rechazado").count()
        finalizadas = cls.objects.filter(estado="finalizado").count()
        activas = total - rechazadas - finalizadas

        # Solicitudes por tipo
        relevamientos = cls.objects.filter(tipo=cls.TIPO_RELEVAMIENTO).count()
        actualizaciones = cls.objects.filter(
            tipo=cls.TIPO_ACTUALIZACION).count()

        return {
            'total': total,
            'rechazadas': rechazadas,
            'finalizadas': finalizadas,
            'activas': activas,
            'relevamientos': relevamientos,
            'actualizaciones': actualizaciones,
            'porcentaje_exito': (finalizadas / total * 100) if total > 0 else 0,
        }

    @classmethod
    def obtener_estadisticas_por_estado(cls):
        """Obtener conteo de solicitudes por cada estado"""
        estados = dict(cls.ESTADOS)
        estadisticas = {}

        for estado_codigo, estado_nombre in estados.items():
            conteo = cls.objects.filter(estado=estado_codigo).count()
            estadisticas[estado_codigo] = {
                'nombre': estado_nombre,
                'conteo': conteo,
                'porcentaje': (conteo / cls.objects.count() * 100) if cls.objects.count() > 0 else 0
            }

        return estadisticas

    @classmethod
    def obtener_solicitudes_recientes(cls, limite=10):
        """Obtener las solicitudes más recientes"""
        return cls.objects.select_related('colonia', 'creado_por').order_by('-fecha_creacion')[:limite]

    @classmethod
    def obtener_tiempos_promedio(cls):
        """Obtener tiempos promedio por etapa"""
        tiempos = {}

        # Tiempo promedio de digitalización (solo solicitudes con tiempo registrado)
        tiempo_digitalizacion = cls.objects.exclude(
            tiempo_digitalizacion__isnull=True
        ).aggregate(
            promedio=Avg('tiempo_digitalizacion')
        )['promedio']

        # Tiempo promedio de análisis
        tiempo_analisis = cls.objects.exclude(
            tiempo_analisis__isnull=True
        ).aggregate(
            promedio=Avg('tiempo_analisis')
        )['promedio']

        # Tiempo promedio de campo
        tiempo_campo = cls.objects.exclude(
            tiempo_campo__isnull=True
        ).aggregate(
            promedio=Avg('tiempo_campo')
        )['promedio']

        # Tiempo promedio total
        tiempo_total = cls.objects.exclude(
            tiempo_total__isnull=True
        ).aggregate(
            promedio=Avg('tiempo_total')
        )['promedio']

        return {
            'digitalizacion': tiempo_digitalizacion,
            'analisis': tiempo_analisis,
            'campo': tiempo_campo,
            'total': tiempo_total,
        }

    # También puedes agregar propiedades para acceder fácilmente desde las instancias
    @property
    def es_activa(self):
        """Determinar si la solicitud está activa (no rechazada ni finalizada)"""
        return self.estado not in ["rechazado", "finalizado"]

    @property
    def es_finalizada(self):
        """Determinar si la solicitud está finalizada"""
        return self.estado == "finalizado"

    @property
    def es_rechazada(self):
        """Determinar si la solicitud está rechazada"""
        return self.estado == "rechazado"

    class Meta:
        verbose_name = "Solicitud de relevamiento"
        verbose_name_plural = "Solicitudes de relevamiento"
        ordering = ["-fecha_creacion"]
        permissions = [
            ("cambiar_estado", "Puede cambiar el estado de la solicitud"),
            ("reasignar_grupo", "Puede reasignar el grupo de la solicitud"),
            ("ver_estadisticas", "Puede ver estadísticas de las solicitudes"),
        ]

    def __str__(self):
        return f"Solicitud {self.pk} - {self.colonia} ({self.get_estado_display()})"

    # --- LÓGICA DE NEGOCIO ---

    def clean(self):
        """Validaciones antes de guardar"""
        super().clean()

        # Validar que no haya más de una solicitud activa por colonia
        # SOLO si colonia está asignada (evita el error RelatedObjectDoesNotExist)
        if hasattr(self, 'colonia_id') and self.colonia_id and self.estado not in ["rechazado", "finalizado"]:
            # Construir el queryset para buscar solicitudes activas en la misma colonia
            queryset = SolicitudRelevamiento.objects.filter(
                colonia_id=self.colonia_id,  # Usar colonia_id en lugar de colonia
                estado__in=[estado for estado, _ in self.ESTADOS
                            if estado not in ["rechazado", "finalizado"]]
            )
            # Si la instancia ya existe (tiene pk), excluirla del queryset
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

            if queryset.exists():
                # Usar get() para obtener el nombre de la colonia si es necesario
                try:
                    colonia = Colonia.objects.get(pk=self.colonia_id)
                    raise ValidationError(
                        f"Ya existe una solicitud activa para la colonia {colonia.nombre}"
                    )
                except Colonia.DoesNotExist:
                    raise ValidationError(
                        "Ya existe una solicitud activa para esta colonia")

    def save(self, *args, **kwargs):
        """Guardar con lógica de estados y tiempos"""
        es_nuevo = not self.pk
        ahora = timezone.now()

        # Variables para tracking
        estado_anterior = None
        estado_cambio = False

        if es_nuevo:
            # Determinar tipo basado en si la colonia ya tiene relevamiento
            if self.colonia.tiene_relevamiento:
                self.tipo = self.TIPO_ACTUALIZACION
                self.estado = "pendiente_asignacion_analista"
            else:
                self.tipo = self.TIPO_RELEVAMIENTO
                self.estado = "pendiente_asignacion_sig"

            # Si no se especifica prioridad, establecer baja por defecto
            if not self.prioridad:
                self.prioridad = "baja"

            # Asignar grupo inicial
            self._asignar_grupo_automaticamente()
        else:
            # Obtener el estado anterior
            try:
                original = SolicitudRelevamiento.objects.get(pk=self.pk)
                estado_anterior = original.estado
            except SolicitudRelevamiento.DoesNotExist:
                estado_anterior = None

            # Verificar si el estado cambió
            if estado_anterior and estado_anterior != self.estado:
                estado_cambio = True

                # Procesar cambio de estado
                self._procesar_cambio_estado(
                    estado_anterior, self.estado, ahora)

                # Reasignar grupo si el estado cambió
                self._asignar_grupo_automaticamente()

                # Limpiar asignación de usuario cuando cambia el grupo
                # EXCEPCIÓN: No limpiar cuando asignamos por primera vez
                if estado_cambio:
                    # Verificar si es la asignación inicial a digitalizador
                    if not (estado_anterior == 'pendiente_asignacion_sig'
                            and self.estado == 'asignado_a_digitalizador'):
                        if self.estado != 'pendiente_revision_sig':
                            # Solo si NO es la asignación inicial, verificar cambios de grupo
                            try:
                                grupo_anterior = original.grupo_asignado
                                if grupo_anterior != self.grupo_asignado:
                                    self.usuario_asignado = None
                                    self.asignado_por = None
                                    self.fecha_asignacion = None
                            except:
                                pass

        # Guardar primero
        super().save(*args, **kwargs)

        # Actualizar colonia si es necesario (solo si hubo cambio de estado)
        if estado_cambio and estado_anterior:
            self._actualizar_colonia_segun_estado(estado_anterior, self.estado)

    def _actualizar_colonia_segun_estado(self, estado_anterior, estado_nuevo):
        """Actualizar el estado de la colonia según cambios en la solicitud"""
        if estado_nuevo == "finalizado" and estado_anterior != "finalizado":
            if self.tipo == self.TIPO_RELEVAMIENTO:
                if not self.colonia.tiene_relevamiento:
                    Colonia.objects.filter(pk=self.colonia.pk).update(
                        tiene_relevamiento=True
                    )
                    # Opcional: Actualizar la instancia en memoria
                    self.colonia.refresh_from_db()

        elif estado_nuevo != "finalizado" and estado_anterior == "finalizado":
            if self.tipo == self.TIPO_RELEVAMIENTO:
                # Verificar si hay otros relevamientos finalizados
                otros_finalizados = SolicitudRelevamiento.objects.filter(
                    colonia=self.colonia,
                    estado="finalizado",
                    tipo=self.TIPO_RELEVAMIENTO
                ).exclude(pk=self.pk)

                if not otros_finalizados.exists():
                    Colonia.objects.filter(pk=self.colonia.pk).update(
                        tiene_relevamiento=False
                    )
                    # Opcional: Actualizar la instancia en memoria
                    self.colonia.refresh_from_db()

    def _procesar_cambio_estado(self, estado_anterior, estado_nuevo, ahora):
        """Procesar lógica al cambiar de estado"""

        # Registrar fechas específicas
        if estado_nuevo == "aprobado_para_campo":
            self.fecha_aprobacion_campo = ahora
        elif estado_nuevo == "en_ejecucion_campo":
            self.fecha_inicio_campo = ahora
        elif estado_nuevo == "pendiente_cierre" and estado_anterior == "en_ejecucion_campo":
            self.fecha_fin_campo = ahora
        elif estado_nuevo == "finalizado":
            self.fecha_finalizacion = ahora

        # Calcular tiempos de etapas
        estados_inicio = [
            "en_proceso_digitalizacion",
            "en_proceso_analisis",
            "en_ejecucion_campo"
        ]

        # Si el nuevo estado inicia una etapa, registrar inicio
        if estado_nuevo in estados_inicio:
            self.fecha_inicio_etapa = ahora

        # Si salimos de una etapa, calcular duración
        if estado_anterior == "en_proceso_digitalizacion" and self.fecha_inicio_etapa:
            duracion = ahora - self.fecha_inicio_etapa
            self.tiempo_digitalizacion = (
                self.tiempo_digitalizacion or timezone.timedelta(0)) + duracion

        if estado_anterior == "en_proceso_analisis" and self.fecha_inicio_etapa:
            duracion = ahora - self.fecha_inicio_etapa
            self.tiempo_analisis = (
                self.tiempo_analisis or timezone.timedelta(0)) + duracion

        if estado_anterior == "en_ejecucion_campo" and self.fecha_inicio_etapa:
            duracion = ahora - self.fecha_inicio_etapa
            self.tiempo_campo = (
                self.tiempo_campo or timezone.timedelta(0)) + duracion

        # Calcular tiempo total al finalizar
        if estado_nuevo == "finalizado":
            self.tiempo_total = ahora - self.fecha_creacion

            # IMPORTANTE: Solo actualizar si es un RELEVAMIENTO NUEVO
            if self.tipo == self.TIPO_RELEVAMIENTO:
                # Verificar que realmente no tenía relevamiento
                if not self.colonia.tiene_relevamiento:
                    self.colonia.tiene_relevamiento = True
                    # Usar update para evitar recursión
                    Colonia.objects.filter(pk=self.colonia.pk).update(
                        tiene_relevamiento=True
                    )

        # Si se revierte la finalización (solo admin puede hacer esto)
        if estado_anterior == "finalizado" and estado_nuevo != "finalizado":
            # Solo revertir si era un relevamiento nuevo
            if self.tipo == self.TIPO_RELEVAMIENTO:
                # Considerar si hay otras solicitudes finalizadas

                # Contar si hay otras solicitudes finalizadas para esta colonia
                otras_finalizadas = SolicitudRelevamiento.objects.filter(
                    colonia=self.colonia,
                    estado="finalizado",
                    tipo=self.TIPO_RELEVAMIENTO
                ).exclude(pk=self.pk)

                # Si NO hay otras relevamientos finalizados, entonces sí revertir
                if not otras_finalizadas.exists():
                    self.colonia.tiene_relevamiento = False
                    Colonia.objects.filter(pk=self.colonia.pk).update(
                        tiene_relevamiento=False
                    )

    def _asignar_grupo_automaticamente(self):
        """Asignar grupo automáticamente basado en el estado actual"""
        if self.estado in ['asignado_a_digitalizador', 'en_proceso_digitalizacion', 'pendiente_revision_sig'] and self.usuario_asignado:
            # Mantener la asignación existente
            pass
        else:
            # Solo limpiar si no hay usuario asignado o no estamos en estados de asignación activa
            self.usuario_asignado = None
            self.asignado_por = None
            self.fecha_asignacion = None

        # Obtener nombres de grupos para este estado
        nombres_grupos = self.GRUPOS_POR_ESTADO.get(self.estado, [])

        if isinstance(nombres_grupos, dict):
            nombres_grupos = nombres_grupos.get(self.tipo, [])

        if not nombres_grupos:
            self.grupo_asignado = None
            return True

        # 1. Intentar con flujo de trabajo configurado
        try:
            flujo = FlujoTrabajo.objects.filter(activo=True).first()
            if flujo:
                grupo = flujo.obtener_grupo_por_estado(self.estado)
                if grupo:
                    self.grupo_asignado = grupo
                    return True
        except Exception:
            pass

        # 2. Buscar por nombres de grupos
        if nombres_grupos:
            query = Q()
            for nombre in nombres_grupos:
                query |= Q(nombre__icontains=nombre) | Q(
                    descripcion__icontains=nombre)

            query &= Q(activo=True)

            grupo = Grupo.objects.filter(query).first()
            if grupo:
                self.grupo_asignado = grupo
                return True

        return False

    def puede_gestionar(self, usuario):
        """Verificar si un usuario puede gestionar esta solicitud"""
        if usuario.is_superuser:
            return True

        if usuario == self.creado_por:
            return True

        if self.usuario_asignado == usuario:
            return True

        if self.grupo_asignado and self.grupo_asignado.lider == usuario:
            return True

        # Verificar si el usuario pertenece al grupo asignado
        if self.grupo_asignado and usuario in self.grupo_asignado.miembros.all():
            return True

        return False

    def puede_cambiar_estado(self, usuario, nuevo_estado=None):
        """Verificar si el usuario puede cambiar al estado especificado"""
        if not self.puede_gestionar(usuario):
            return False

        if nuevo_estado:
            estados_permitidos = self.obtener_estados_siguientes(usuario)
            return nuevo_estado in estados_permitidos

        return True

    def obtener_estados_siguientes(self, usuario):
        """Obtener los estados a los que se puede cambiar desde el estado actual"""

        # Definir transiciones básicas
        transiciones = {
            # Flujo SIG (colonias nuevas)
            "pendiente_asignacion_sig": ["asignado_a_digitalizador"],
            "asignado_a_digitalizador": ["en_proceso_digitalizacion"],
            "en_proceso_digitalizacion": ["pendiente_revision_sig", "rechazado"],
            "pendiente_revision_sig": ["pendiente_aprobacion_campo", "rechazado"],

            # Flujo Análisis
            "pendiente_asignacion_analista": ["en_proceso_analisis"],
            "en_proceso_analisis": ["pendiente_aprobacion_campo", "rechazado"],
            "pendiente_aprobacion_campo": ["aprobado_para_campo", "rechazado"],

            # Flujo Campo
            "aprobado_para_campo": ["asignado_coordinacion"],
            "asignado_coordinacion": ["preparacion_campo"],
            "preparacion_campo": ["en_ejecucion_campo"],
            "en_ejecucion_campo": ["pendiente_cierre"],
            "pendiente_cierre": ["finalizado"],

            # Estados finales
            "rechazado": [],
            "finalizado": [],
        }

        # Administradores pueden revertir a estados anteriores
        if usuario.is_superuser or usuario.has_perm('solicitudes.cambiar_estado'):
            estados_permitidos = list(transiciones.get(self.estado, []))

            # Agregar opción de revertir rechazo
            if self.estado == "rechazado":
                if self.tipo == self.TIPO_RELEVAMIENTO:
                    estados_permitidos.append("pendiente_asignacion_sig")
                else:
                    estados_permitidos.append("pendiente_asignacion_analista")

            return estados_permitidos

        return transiciones.get(self.estado, [])

    def asignar_usuario(self, usuario, asignado_por):
        """Asignar usuario específico a la solicitud"""
        if not self.grupo_asignado:
            raise ValidationError("La solicitud no tiene grupo asignado")

        # Verificar que el usuario pertenezca al grupo
        if not self.grupo_asignado.miembros.filter(id=usuario.id).exists():
            raise ValidationError(
                f"El usuario no pertenece al grupo {self.grupo_asignado}")

        self.usuario_asignado = usuario
        self.asignado_por = asignado_por
        self.fecha_asignacion = timezone.now()
        self.save()

    def obtener_tiempo_transcurrido(self):
        """Obtener tiempo transcurrido desde la creación"""
        if self.fecha_creacion:
            return timezone.now() - self.fecha_creacion
        return timezone.timedelta(0)

    def obtener_tiempo_etapa_actual(self):
        """Obtener tiempo transcurrido en la etapa actual"""
        if self.fecha_inicio_etapa:
            return timezone.now() - self.fecha_inicio_etapa
        return timezone.timedelta(0)

    def es_urgente(self):
        """Determinar si la solicitud es urgente basado en tiempo"""
        tiempo_transcurrido = self.obtener_tiempo_transcurrido()

        # Definir umbrales de urgencia (puedes ajustar estos valores)
        if self.estado in ["en_proceso_digitalizacion", "en_proceso_analisis", "en_ejecucion_campo"]:
            # Si está en proceso más de 30 días
            return tiempo_transcurrido.days > 30

        if self.estado in ["pendiente_asignacion_sig", "pendiente_asignacion_analista", "pendiente_revision_sig", "pendiente_revision_analista"]:
            # Si está pendiente más de 2 días
            return tiempo_transcurrido.days > 2

        return False

    @property
    def etapa_actual(self):
        """Obtener la etapa actual del proceso"""
        if "sig" in self.estado:
            return "SIG"
        elif "analisis" in self.estado or "analista" in self.estado:
            return "Análisis"
        elif "campo" in self.estado or "coordinacion" in self.estado:
            return "Campo"
        elif self.estado in ["rechazado", "finalizado"]:
            return "Finalizado"
        else:
            return "Pendiente"

    @classmethod
    def obtener_solicitudes_por_grupo(cls, grupo):
        """Obtener todas las solicitudes asignadas a un grupo"""
        return cls.objects.filter(grupo_asignado=grupo).exclude(
            estado__in=["rechazado", "finalizado"]
        )

    @classmethod
    def obtener_solicitudes_por_usuario(cls, usuario):
        """Obtener todas las solicitudes asignadas a un usuario"""
        return cls.objects.filter(usuario_asignado=usuario).exclude(
            estado__in=["rechazado", "finalizado"]
        )


class SolicitudRelevamientoAudit(models.Model):
    """Modelo para auditar cambios en las solicitudes"""

    solicitud = models.ForeignKey(
        SolicitudRelevamiento,
        on_delete=models.CASCADE,
        related_name="auditorias",
        verbose_name="Solicitud"
    )
    campo = models.CharField(
        max_length=50,
        verbose_name="Campo modificado",
        null=True,
        blank=True
    )
    valor_anterior = models.TextField(
        blank=True,
        verbose_name="Valor anterior"
    )
    valor_nuevo = models.TextField(
        blank=True,
        verbose_name="Valor nuevo"
    )
    cambiado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Modificado por"
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de modificación"
    )
    comentario = models.TextField(
        blank=True,
        verbose_name="Comentario"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dirección IP"
    )

    class Meta:
        verbose_name = "Auditoría de solicitud"
        verbose_name_plural = "Auditorías de solicitudes"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=['solicitud', 'fecha']),
            models.Index(fields=['campo', 'fecha']),
        ]

    def __str__(self):
        return f"Auditoría {self.pk} - {self.solicitud} - {self.campo}"
