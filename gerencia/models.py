from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from administrador.models import Grupo, FlujoTrabajo, TipoObjetivo
from django.db.models import Q
from core.models import Colonia
from django.db.models import Avg

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
        # ESTADOS SIG
        ("pendiente_asignacion_sig", "Pendiente de Asignación SIG"),
        ("asignado_a_digitalizador", "Asignado a Digitalizador"),
        ("en_proceso_digitalizacion", "En Proceso de Digitalización"),
        ("pendiente_revision_sig", "Pendiente de Revisión SIG"),
        ("rechazado", "Rechazado"),

        # ESTADOS ANALISIS
        ("pendiente_asignacion_analista", "Pendiente de Asignación Análisis"),
        ("asignado_a_analista", "Asignado a Analista"),
        ("en_proceso_analisis", "En Proceso de Análisis"),
        ("pendiente_revision_analista", "Pendiente de Revisión Análisis"),

        # APROBACIONES
        ("aprobado_para_campo", "Aprobado para Campo"),

        # ESTADOS COORDINACION
        ("asignado_coordinacion", "Asignado a Coordinación"),
        ("orden_trabajo_generada", "Orden de Trabajo Generada"),

        # ESTADOS RELEVAMIENTO
        ("asignado_relevadores", "Asignado a Relevadores"),
        ("en_ejecucion_campo", "En Ejecución de Campo"),
        ("pendiente_cierre", "Pendiente de Cierre"),
        ("finalizado", "Finalizado"),
    ]

    GRUPOS_POR_ESTADO = {
        # Estados SIG
        "pendiente_asignacion_sig": ["SIG"],
        "asignado_a_digitalizador": ["SIG"],
        "en_proceso_digitalizacion": ["SIG"],
        "pendiente_revision_sig": ["SIG"],
        "rechazado": ["SIG", "ANALISIS", "COORDINACION Y MONITOREO", "COORDINACION", "MONITOREO"],

        # Estados Análisis
        "pendiente_asignacion_analista": ["ANALISIS"],
        "asignado_a_analista": ["ANALISIS"],
        "en_proceso_analisis": ["ANALISIS"],
        "pendiente_revision_analista": ["ANALISIS"],

        # Aprobación campo
        "aprobado_para_campo": {
            "relevamiento": ["SIG"],
            "actualizacion": ["ANALISIS"]
        },

        # Coordinación
        "asignado_coordinacion": ["COORDINACION Y MONITOREO", "COORDINACION", "MONITOREO"],
        "orden_trabajo_generada": ["COORDINACION Y MONITOREO", "COORDINACION", "MONITOREO"],

        # Relevamiento
        "asignado_relevadores": ["RELEVAMIENTO"],
        "en_ejecucion_campo": ["RELEVAMIENTO"],
        "pendiente_cierre": ["RELEVAMIENTO"],
        "finalizado": ["RELEVAMIENTO"],
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

      # Indicador booleano adicional para marcar el relevamiento como terminado (útil para reportes y filtros)
    relevamiento_terminado = models.BooleanField(
        default=False,
        verbose_name="Relevamiento Terminado",
        help_text="Marca si el relevamiento fue terminado o completado."
    )
    # Indicador booleano adicional para marcar la actualización como terminada (útil para reportes y filtros)
    actualizacion_terminado = models.BooleanField(
        default=False,
        verbose_name="Actualización Terminada",
        help_text="Marca si la actualización fue terminada o completada."
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


    usuario_analista = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_analizadas",
        verbose_name="Analista asignado"
    )

    coordinador_asignado = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_coordinadas",
        verbose_name="Coordinador asignado"
    )

    # Campo para saber quién hizo la última asignación
    ultima_asignacion_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ultimas_asignaciones",
        verbose_name="Última asignación por"
    )

    # Mantener el usuario_asignado actual (puede ser cualquiera)
    usuario_asignado = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tareas_asignadas_actualmente",
        verbose_name="Usuario asignado actualmente"
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

    numero_orden_trabajo = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Número de Orden de Trabajo"
    )
    fecha_generacion_orden = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha generación orden"
    )
    usuario_generador_orden = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes_generadas",
        verbose_name="Generador de orden"
    )

    # Campo para relevadores asignados (si son múltiples)
    coordinador_campo = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_coordinadas_campo',
        verbose_name="Coordinador de campo"
    )
    subcoordinadores = models.ManyToManyField(
        User,
        blank=True,
        related_name='solicitudes_subcoordinadas',
        verbose_name="Subcoordinadores"
    )
    choferes = models.ManyToManyField(
        User,
        blank=True,
        related_name='solicitudes_chofer',
        verbose_name="Choferes"
    )

    relevadores_asignados = models.ManyToManyField(
        User,
        blank=True,
        related_name="relevamientos_asignados",
        verbose_name="Relevadores asignados"
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
    cambiado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auditorias_realizadas'
    )

    @classmethod
    def obtener_estadisticas(cls):
        """Obtener estadísticas generales de solicitudes"""
        total = cls.objects.count()
        rechazadas = cls.objects.filter(estado="rechazado").count()
        finalizadas = cls.objects.filter(estado="finalizado").count()
        activas = total - rechazadas - finalizadas

        # Solicitudes por tipo
        # Contar como 'relevamientos' todas las solicitudes que tengan alguno de los
        # indicadores de finalización: `relevamiento_terminado` o `actualizacion_terminado`.
        relevamientos = cls.objects.filter(relevamiento_terminado=True).count()

        # Mantener la métrica de actualizaciones por tipo para compatibilidad
        actualizaciones = cls.objects.filter(tipo=cls.TIPO_ACTUALIZACION).count()

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

    def generar_orden_trabajo(self, usuario_generador, numero_orden=None):
        """Generar orden de trabajo"""
        if self.estado != "asignado_coordinacion":
            raise ValidationError(
                "Solo se puede generar orden desde 'Asignado a coordinacion")

        if not numero_orden:
            numero_orden = f"OT-{self.pk}-{timezone.now().strftime('%Y%m%d')}"

        self.numero_orden_trabajo = numero_orden
        self.usuario_generador_orden = usuario_generador
        self.estado = "orden_trabajo_generada"
        self.save()

        SolicitudRelevamientoAudit.objects.create(
            solicitud=self,
            campo='estado',
            valor_anterior="asignado_coordinacion",
            valor_nuevo="orden_trabajo_generada",
            cambiado_por=usuario_generador,
            comentario=f"Orden de trabajo {numero_orden} generada por {usuario_generador.get_full_name()}"
        )

        return numero_orden

    def asignar_relevadores(self, relevadores, asignado_por, motivo=""):
        """Asignar múltiples relevadores"""
        if self.estado != "orden_trabajo_generada":
            raise ValidationError(
                "Solo se puede asignar relevadores con orden generada")

        # Guardar relevadores en ManyToMany
        self.relevadores_asignados.set(relevadores)

        # Asignar el primero como usuario principal
        if relevadores:
            self.usuario_asignado = relevadores[0]

        self.asignado_por = asignado_por
        self.ultima_asignacion_por = asignado_por
        self.fecha_asignacion = timezone.now()
        self.estado = "asignado_relevadores"
        self.save()

        # Auditoría detallada
        nombres_relevadores = ", ".join(
            [r.get_full_name() for r in relevadores])
        comentario = f"Relevadores asignados: {nombres_relevadores} por {asignado_por.get_full_name()}"
        if motivo:
            comentario += f". Motivo: {motivo}"

        SolicitudRelevamientoAudit.objects.create(
            solicitud=self,
            campo='relevadores_asignados',
            valor_anterior="",
            valor_nuevo=nombres_relevadores,
            cambiado_por=asignado_por,
            comentario=comentario
        )

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
                # Si ya hay un analista anterior, sugerirlo automáticamente
                anterior = SolicitudRelevamiento.objects.filter(
                    colonia=self.colonia,
                    usuario_analista__isnull=False
                ).last()
                if anterior and anterior.usuario_analista:
                    self.usuario_analista = anterior.usuario_analista
                    self.usuario_asignado = anterior.usuario_analista
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

        # TRANSICIÓN AUTOMÁTICA: aprobado_para_campo → asignado_coordinacion
        if estado_nuevo == "aprobado_para_campo":
            # Registrar fecha de aprobación
            self.fecha_aprobacion_campo = ahora

            # Cambiar automáticamente a asignado_coordinacion
            self.estado = "asignado_coordinacion"

            # Crear auditoría de la transición automática
            # (se creará después del save principal)
            self._crear_auditoria_auto_transicion = True

        # Registrar otras fechas específicas
        if self.estado == "en_ejecucion_campo":
            self.fecha_inicio_campo = ahora
        elif self.estado == "pendiente_cierre" and estado_anterior == "en_ejecucion_campo":
            self.fecha_fin_campo = ahora
        elif self.estado == "finalizado":
            self.fecha_finalizacion = ahora

        # Calcular tiempos de etapas
        estados_inicio = [
            "en_proceso_digitalizacion",
            "en_proceso_analisis",
            "en_ejecucion_campo"
        ]

        # Si el nuevo estado inicia una etapa, registrar inicio
        if self.estado in estados_inicio:
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
        if self.estado == "finalizado":
            self.tiempo_total = ahora - self.fecha_creacion

            if self.tipo == self.TIPO_RELEVAMIENTO:
                if not self.colonia.tiene_relevamiento:
                    self.colonia.tiene_relevamiento = True
                    Colonia.objects.filter(pk=self.colonia.pk).update(
                        tiene_relevamiento=True
                    )

        # Si se revierte la finalización
        if estado_anterior == "finalizado" and self.estado != "finalizado":
            if self.tipo == self.TIPO_RELEVAMIENTO:
                otras_finalizadas = SolicitudRelevamiento.objects.filter(
                    colonia=self.colonia,
                    estado="finalizado",
                    tipo=self.TIPO_RELEVAMIENTO
                ).exclude(pk=self.pk)

                if not otras_finalizadas.exists():
                    self.colonia.tiene_relevamiento = False
                    Colonia.objects.filter(pk=self.colonia.pk).update(
                        tiene_relevamiento=False
                    )

    def _asignar_grupo_automaticamente(self):
        """Asignar grupo automáticamente basado en el estado actual"""
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
        if self.grupo_asignado and usuario in self.grupo_asignado.usuarios.all():
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
            "pendiente_revision_sig": ["aprobado_para_campo", "rechazado"],

            # Flujo Análisis
            "pendiente_asignacion_analista": ["asignado_a_analista"],
            "asignado_a_analista": ["en_proceso_analisis"],
            "en_proceso_analisis": ["pendiente_revision_analista", "rechazado"],
            "pendiente_revision_analista": ["aprobado_para_campo", "rechazado"],


            # Flujo Coordinación
            "aprobado_para_campo": ["asignado_coordinacion"],
            "asignado_coordinacion": ["orden_trabajo_generada"],
            "orden_trabajo_generada": ["asignado_relevadores", "rechazado"],

            # Flujo Campo
            "asignado_relevadores": ["en_ejecucion_campo"],
            "en_ejecucion_campo": ["pendiente_cierre"],
            "pendiente_cierre": ["finalizado"],

            # Estados finales
            "rechazado": [],
            "finalizado": []
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

    def asignar_digitalizador(self, usuario, asignado_por):
        """Asignar digitalizador específico"""
        if not self.grupo_asignado or "SIG" not in self.grupo_asignado.nombre.upper():
            raise ValidationError("La solicitud no está asignada al grupo SIG")

        # Verificar que el usuario pertenezca al grupo SIG
        if not self.grupo_asignado.usuarios.filter(id=usuario.id).exists():
            raise ValidationError(
                f"El usuario no pertenece al grupo {self.grupo_asignado}")

        # Actualizar asignación en la solicitud (usuario_asignado sigue existiendo)
        self.usuario_asignado = usuario
        self.asignado_por = asignado_por
        self.ultima_asignacion_por = asignado_por
        self.fecha_asignacion = timezone.now()
        self.save()

        # Registrar el evento en el nuevo modelo de sig (evitar import circular global)
        try:
            from sig.models import AsignacionDigitalizador
            AsignacionDigitalizador.objects.create(
                solicitud=self,
                registrado_por=asignado_por,
                usuario_asignado=usuario,
                # fecha_asignacion se llena con auto_now_add
            )
        except Exception:
            # Si por alguna razón no existe el modelo aun, continuar pero dejar auditoría
            pass

        # Registrar auditoría usando el mismo campo para trazabilidad histórica
        SolicitudRelevamientoAudit.objects.create(
            solicitud=self,
            campo='usuario_digitalizador',
            valor_anterior=None,
            valor_nuevo=f"{usuario.get_full_name()} ({usuario.username})",
            cambiado_por=asignado_por,
            comentario=f"Asignado como digitalizador por {asignado_por.get_full_name()}"
        )

    def asignar_analista(self, usuario, asignado_por):
        """Asignar analista específico"""
        if not self.grupo_asignado or "ANALISIS" not in self.grupo_asignado.nombre.upper():
            raise ValidationError(
                "La solicitud no está asignada al grupo ANÁLISIS")

        if not self.grupo_asignado.usuarios.filter(id=usuario.id).exists():
            raise ValidationError(
                f"El usuario no pertenece al grupo {self.grupo_asignado}")

        self.usuario_analista = usuario
        self.usuario_asignado = usuario
        self.asignado_por = asignado_por
        self.ultima_asignacion_por = asignado_por
        self.fecha_asignacion = timezone.now()
        self.save()

        SolicitudRelevamientoAudit.objects.create(
            solicitud=self,
            campo='usuario_analista',
            valor_anterior=None,
            valor_nuevo=f"{usuario.get_full_name()}",
            cambiado_por=asignado_por,
            comentario=f"Asignado como analista por {asignado_por.get_full_name()}"
        )

    def reasignar_usuario_actual(self, nuevo_usuario, reasignado_por, motivo=""):
        """Reasignar el usuario actual (genérico)"""
        usuario_anterior = self.usuario_asignado

        self.usuario_asignado = nuevo_usuario
        self.asignado_por = reasignado_por
        self.ultima_asignacion_por = reasignado_por
        self.fecha_asignacion = timezone.now()
        self.save()

        # Registrar auditoría detallada
        comentario = f"Reasignado de {usuario_anterior.get_full_name() if usuario_anterior else 'Ninguno'} "
        comentario += f"a {nuevo_usuario.get_full_name()} por {reasignado_por.get_full_name()}"
        if motivo:
            comentario += f". Motivo: {motivo}"

        SolicitudRelevamientoAudit.objects.create(
            solicitud=self,
            campo='usuario_asignado',
            valor_anterior=f"{usuario_anterior.get_full_name() if usuario_anterior else ''}",
            valor_nuevo=f"{nuevo_usuario.get_full_name()}",
            cambiado_por=reasignado_por,
            comentario=comentario
        )

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

    @property
    def responsable_actual(self):
        """Obtener el responsable actual según el estado"""
        if "digitalizacion" in self.estado:
            # Intentar obtener la última asignación registrada en sig.AsignacionDigitalizador
            try:
                from sig.models import AsignacionDigitalizador
                ultima = AsignacionDigitalizador.objects.filter(solicitud=self).select_related('usuario_asignado').order_by('-fecha_asignacion').first()
                if ultima and ultima.usuario_asignado:
                    return ultima.usuario_asignado
            except Exception:
                pass
            return self.usuario_asignado
        elif "analisis" in self.estado or "analista" in self.estado:
            return self.usuario_analista
        elif "coordinacion" in self.estado:
            return self.coordinador_asignado
        elif "relevadores" in self.estado:
            return self.usuario_asignado  # Relevador principal
        return self.usuario_asignado

    @property
    def digitalizador_original(self):
        """Obtener el digitalizador original (para trazabilidad)"""
        try:
            from sig.models import AsignacionDigitalizador
            ultima = AsignacionDigitalizador.objects.filter(solicitud=self).select_related('usuario_asignado').order_by('-fecha_asignacion').first()
            if ultima:
                return ultima.usuario_asignado
        except Exception:
            pass
        return None

    @property
    def usuario_digitalizador(self):
        """Compatibilidad: obtener el usuario digitalizador más reciente registrado en `sig.AsignacionDigitalizador`.

        Esto permite mantener plantillas y código que acceden a `solicitud.usuario_digitalizador`.
        """
        try:
            from sig.models import AsignacionDigitalizador
            ultima = AsignacionDigitalizador.objects.filter(solicitud=self).select_related('usuario_asignado').order_by('-fecha_asignacion').first()
            if ultima:
                return ultima.usuario_asignado
        except Exception:
            pass
        return None

    @property
    def analista_original(self):
        """Obtener el analista original (para trazabilidad)"""
        return self.usuario_analista

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

    def obtener_historial_asignaciones(self):
        """Obtener historial completo de asignaciones"""
        return self.auditorias.filter(
            campo__in=['usuario_asignado', 'usuario_digitalizador',
                       'usuario_analista', 'coordinador_asignado']
        ).order_by('-fecha')


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


class Objetivo(models.Model):
    """Modelo para gestionar objetivos anuales por grupo y tipo"""
    
    # Enlazar con el modelo `Grupo` de la app `administrador` para mantener consistencia
    grupo = models.ForeignKey(
        Grupo,
        on_delete=models.PROTECT,
        related_name='objetivos',
        verbose_name='Grupo'
    )
    tipo_objetivo = models.ForeignKey(
        TipoObjetivo,
        on_delete=models.PROTECT,
        related_name='objetivos',
        verbose_name="Tipo de Objetivo",
        help_text="Seleccione el tipo de objetivo del grupo"
    )
    fecha_inicio = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Inicio",
        help_text="Fecha de inicio del objetivo"
    )
    fecha_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha Final",
        help_text="Fecha límite para alcanzar la meta"
    )
    anio = models.IntegerField(
        verbose_name="Año",
        help_text="Año del objetivo (derivado de fecha_fin)"
    )
    meta = models.IntegerField(
        verbose_name="Meta",
        help_text="Cantidad objetivo a alcanzar en el periodo"
    )
    avance_actual = models.IntegerField(
        default=0,
        verbose_name="Avance Actual",
        help_text="Cantidad actual alcanzada"
    )
    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="objetivos_creados",
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
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    
    class Meta:
        verbose_name = "Objetivo"
        verbose_name_plural = "Objetivos"
        ordering = ["-anio", "grupo", "tipo_objetivo"]
        unique_together = ['grupo', 'tipo_objetivo', 'anio']
        indexes = [
            models.Index(fields=['anio', 'grupo']),
            models.Index(fields=['activo', 'anio']),
        ]
    
    def __str__(self):
        grupo_nombre = self.grupo.nombre if hasattr(self.grupo, 'nombre') else str(self.grupo)
        tipo_nombre = self.tipo_objetivo.nombre if self.tipo_objetivo else "Sin tipo"
        return f"{grupo_nombre} - {tipo_nombre} {self.anio}"
    
    def save(self, *args, **kwargs):
        """Calcular automáticamente el año desde fecha_fin y validaciones"""
        # Si no hay fecha_inicio, usar fecha de creación o hoy
        if not self.fecha_inicio:
            if self.pk and self.fecha_creacion:
                self.fecha_inicio = self.fecha_creacion.date()
            else:
                from datetime import date
                self.fecha_inicio = date.today()
        
        # Calcular año desde fecha_fin
        if self.fecha_fin:
            self.anio = self.fecha_fin.year
        elif not self.anio:
            # Si no hay fecha_fin y no hay año, usar año actual
            from datetime import datetime
            self.anio = datetime.now().year
        
        # Validar que el tipo de objetivo pertenece al grupo seleccionado
        if self.tipo_objetivo and self.grupo:
            if self.tipo_objetivo.grupo_id != self.grupo_id:
                raise ValidationError(
                    f"El tipo de objetivo '{self.tipo_objetivo.nombre}' no pertenece al grupo '{self.grupo.nombre}'"
                )
        
        super().save(*args, **kwargs)

    @classmethod
    def get_categoria_grupo(cls, grupo):
        """Detectar categoría aproximada de un `Grupo` (o nombre) basada en su nombre."""
        nombre = grupo.nombre if hasattr(grupo, 'nombre') else str(grupo)
        nombre_upper = nombre.upper()
        if 'RELEVAMIENTO' in nombre_upper or 'CAMPO' in nombre_upper:
            return 'relevamiento'
        if 'SIG' in nombre_upper or 'DIGITALIZADOR' in nombre_upper:
            return 'sig'
        if 'ANALISIS' in nombre_upper or 'ANALISTA' in nombre_upper:
            return 'analisis'
        if 'EXPEDIENTE' in nombre_upper or 'TITULACION' in nombre_upper:
            return 'expedientes'
        return None
    
    @property
    def porcentaje_avance(self):
        """Calcula el porcentaje de avance"""
        if self.meta == 0:
            return 0
        return min(round((self.avance_actual / self.meta) * 100, 1), 100)
    
    @property
    def estado_semaforo(self):
        """Determina el color del semáforo según avance"""
        porcentaje = self.porcentaje_avance
        if porcentaje >= 90:
            return 'success'  # Verde
        elif porcentaje >= 70:
            return 'warning'  # Amarillo
        elif porcentaje >= 50:
            return 'info'     # Azul
        else:
            return 'danger'   # Rojo
    
    @classmethod
    def obtener_objetivos_por_anio(cls, anio):
        """Obtener todos los objetivos de un año específico"""
        return cls.objects.filter(anio=anio, activo=True).select_related('creado_por')
    
    @classmethod
    def obtener_resumen_por_grupo(cls, anio):
        """Obtener resumen de objetivos agrupados por grupo"""
        objetivos = cls.objects.filter(anio=anio, activo=True).select_related('grupo')
        resumen = {}

        # Iterar grupos activos existentes en la app administrador
        for grupo in Grupo.objects.filter(activo=True).order_by('nombre'):
            objetivos_grupo = objetivos.filter(grupo=grupo)
            if objetivos_grupo.exists():
                total_meta = sum(obj.meta for obj in objetivos_grupo)
                total_avance = sum(obj.avance_actual for obj in objetivos_grupo)
                porcentaje = round((total_avance / total_meta * 100), 1) if total_meta > 0 else 0

                resumen[str(grupo.id)] = {
                    'nombre': grupo.nombre,
                    'categoria': cls.get_categoria_grupo(grupo),
                    'total_objetivos': objetivos_grupo.count(),
                    'total_meta': total_meta,
                    'total_avance': total_avance,
                    'porcentaje': porcentaje,
                    'objetivos': list(objetivos_grupo)
                }

        return resumen
