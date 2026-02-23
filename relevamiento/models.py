from django.db import models
from django.contrib.postgres.fields import ArrayField

USO_LOTE_CHOICES = [
    ("acuario_forestal", "Acuario/Forestal"),
    ("forestal_nativa", "Forestal - Nativa"),
    ("barbecho_descanso", "Barbecho - Descanso"),
    ("abandonado", "Abandonado"),
    ("comercial", "Comercial"),
    ("industrial", "Industrial"),
    ("local_politico", "Local Político"),
    ("local_recreativo", "Local Recreativo"),
]

MEJORAS_CHOICES = [
    ("galpon", "Galpón"),
    ("corrales", "Corrales"),
    ("bretes", "Bretes"),
    ("represa", "Represa"),
    ("sanitarios", "Instalaciones Sanitarias"),
    ("pozo", "Pozo"),
    ("tajamares", "Tajamares"),
    ("mangas", "Mangas"),
    ("cercado_perimetral", "Cercado Perimetral"),
    ("silos", "Silos"),
    ("canales_riego", "Canales de Irrigación"),
    ("energia_electrica", "Energía Eléctrica"),
    ("agua_potable", "Agua Potable"),
]

EQUIPAMIENTOS_CHOICES = [
    ("energia_electrica", "Energía Eléctrica"),
    ("agua_corriente", "Agua Corriente"),
    ("cocina", "Cocina"),
    ("bano", "Baño"),
    ("telefono_fijo", "Teléfono Fijo"),
    ("internet", "Internet"),
]

MOD_POST_CHOICES = [
    ("cambio_recurrente", "Cambio de Recurrente"),
    ("correccion_superficie", "Corrección de Superficie"),
    ("ampliacion", "Ampliación"),
]


class Relevamiento(models.Model):
    # 1 - DATOS DEL LOTE
    departamento = models.ForeignKey(
        "core.Departamento", on_delete=models.PROTECT, null=True, blank=True)
    distrito = models.ForeignKey(
        "core.Distrito", on_delete=models.PROTECT, null=True, blank=True)
    colonia = models.ForeignKey(
        "core.Colonia", on_delete=models.PROTECT, null=True, blank=True)

    manzana = models.CharField(max_length=50, blank=True)
    lote_indert = models.CharField(max_length=50, blank=True)
    lote_sirt = models.CharField(max_length=50, blank=True)
    formulario = models.IntegerField(null=True, blank=True)
    observacion_encuesta = models.TextField(blank=True)

    uso_lote = ArrayField(
        base_field=models.CharField(max_length=50, choices=USO_LOTE_CHOICES),
        blank=True,
        null=True,
        default=list,
    )

    # 2 - DOCUMENTOS DEL LOTE
    nro_titulo = models.CharField(max_length=200, blank=True)

    # 3 - DATOS DE LA OCUPACIÓN
    TIPO_LOTE_CHOICES = [("agricola", "Agrícola"),
                         ("quinta", "Quinta"), ("urbana", "Urbana")]

    tipo_lote = models.CharField(
        max_length=20, choices=TIPO_LOTE_CHOICES, blank=True)

    COND_VIVIENDA_CHOICES = [
        ("presente", "Presente"),
        ("ausente", "Ausente"),
        ("sin_vivienda", "Sin vivienda"),
        ("servicio", "Servicio"),
    ]
    condicion_vivienda = models.CharField(
        max_length=20, choices=COND_VIVIENDA_CHOICES, blank=True)

    COND_ENCUESTADO_CHOICES = [
        ("titular", "Titular"),
        ("ocupante", "Ocupante"),
        ("pariente", "Pariente o no pariente"),
        ("otro", "Otro"),
    ]

    condicion_encuestado = models.CharField(
        max_length=20, choices=COND_ENCUESTADO_CHOICES, blank=True)

    superficie_ha = models.FloatField(null=True, blank=True)
    dimensiones = models.CharField(max_length=200, blank=True)
    vive_en_lote = models.BooleanField(default=False)

    # Si no vive en el lote: datos de residencia
    residencia_manzana = models.CharField(max_length=50, blank=True)
    residencia_lote = models.CharField(max_length=50, blank=True)
    quien_es_el_ocupante = models.CharField(max_length=200, blank=True)
    parentesco = models.CharField(max_length=200, blank=True)

    # 4 - USO DE LA TIERRA Y MEJORAS
    produccion_agricola_ha = models.FloatField(default=0, blank=True)
    produccion_ganadera_ha = models.FloatField(default=0, blank=True)
    reforestado_ha = models.FloatField(default=0, blank=True)
    bosque_natural_ha = models.FloatField(default=0, blank=True)
    barbecho_ha = models.FloatField(default=0, blank=True)

    mejoras = ArrayField(
        base_field=models.CharField(max_length=50, choices=MEJORAS_CHOICES),
        blank=True,
        null=True,
        default=list,
    )

    # 5 - DATOS DE LA VIVIENDA (se agrupan en un submodelo)

    # 7 - FINAL DE LA ENTREVISTA
    ESTADO_ENTREVISTA = [
        ("completa", "Completa"),
        ("rechazo", "Rechazo"),
        ("parcial", "Parcial"),
        ("en_conflicto", "En Conflicto"),
    ]
    estado_entrevista = models.CharField(
        max_length=20, choices=ESTADO_ENTREVISTA, blank=True)
    firmo_solicitud = models.BooleanField(default=False)

    modificaciones_post = ArrayField(
        base_field=models.CharField(max_length=50, choices=MOD_POST_CHOICES),
        blank=True,
        null=True,
        default=list,
        help_text="Lista de claves de modificaciones",
    )

    # Vinculación con la Orden de Trabajo de coordinación (OBLIGATORIO)
    orden_trabajo = models.ForeignKey(
        'coordinacion.OrdenTrabajo',
        on_delete=models.PROTECT,
        related_name='relevamientos',
        verbose_name="Orden de Trabajo",
        help_text="Todo relevamiento debe estar asociado a una orden de trabajo"
    )

    # Encuestador que realizó el relevamiento
    encuestador = models.ForeignKey(
        'administrador.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='relevamientos_realizados',
        verbose_name="Encuestador"
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Relevamiento #{self.pk} - {self.colonia or 'sin colonia'}"


class Documento(models.Model):
    TIPO = [
        ("recibo", "Recibos"),
        ("constancia_ocupacion", "Constancia de ocupacion"),
        ("plano", "Plano"),
        ("transferencia", "Transferencia"),
        ("otros", "Otros"),
    ]

    relevamiento = models.ForeignKey(
        Relevamiento, on_delete=models.CASCADE, related_name="documentos")
    tipo = models.CharField(max_length=30, choices=TIPO)
    archivo = models.FileField(
        upload_to="relevamiento/docs/", blank=True, null=True)
    nombre_archivo = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.tipo} - {self.nombre_archivo or (self.archivo.name if self.archivo else '')}"


class Cultivo(models.Model):
    TIPO_SIEMBRA = [("temporal", "Temporal"), ("permanente", "Permanente")]
    relevamiento = models.ForeignKey(
        Relevamiento, on_delete=models.CASCADE, related_name="cultivos")
    descripcion = models.CharField(max_length=200)
    tipo_siembra = models.CharField(max_length=20, choices=TIPO_SIEMBRA)
    hectareas = models.FloatField()

    def __str__(self):
        return f"{self.descripcion} ({self.hectareas} Ha)"


class ProduccionGanadera(models.Model):
    relevamiento = models.ForeignKey(
        Relevamiento, on_delete=models.CASCADE, related_name="producciones_ganaderas")
    descripcion = models.CharField(max_length=200)
    cantidad = models.IntegerField()

    def __str__(self):
        return f"{self.descripcion} x {self.cantidad}"


class Vivienda(models.Model):
    PAREDES = [("ladrillo", "Ladrillo"), ("madera", "Madera"),
               ("adobe", "Adobe"), ("mixto", "Mixto"), ("otro", "Otro")]
    PISOS = [("ceramica", "Cerámica"), ("cemento", "Cemento"),
             ("tierra", "Tierra"), ("madera", "Madera"), ("otro", "Otro")]
    TECHOS = [("chapa", "Chapa de Zinc"), ("teja", "Teja"),
              ("paja", "Paja"), ("losa", "Losa"), ("otro", "Otro")]
    AGUA = [("pozo", "Pozo"), ("red_publica", "Red Pública"),
            ("arroyo", "Arroyo/Río"), ("aljibe", "Aljibe"), ("otro", "Otro")]
    BANO = [("letrina", "Letrina"), ("pozo_ciego", "Baño con Pozo Ciego"),
            ("alcantarillado", "Baño con Alcantarillado"), ("no_tiene", "No Tiene")]

    relevamiento = models.OneToOneField(
        Relevamiento, on_delete=models.CASCADE, related_name="vivienda", null=True, blank=True)
    paredes = models.CharField(max_length=20, choices=PAREDES, blank=True)
    piso = models.CharField(max_length=20, choices=PISOS, blank=True)
    techo = models.CharField(max_length=20, choices=TECHOS, blank=True)
    piezas = models.IntegerField(null=True, blank=True)
    agua_proviene = models.CharField(max_length=20, choices=AGUA, blank=True)
    tipo_bano = models.CharField(max_length=20, choices=BANO, blank=True)

    equipamientos = ArrayField(
        base_field=models.CharField(
            max_length=50, choices=EQUIPAMIENTOS_CHOICES),
        blank=True,
        null=True,
        default=list,
        help_text="Lista de equipamientos: energia, agua, cocina, baño, telefono, internet",
    )

    def __str__(self):
        return f"Vivienda Relevamiento #{self.relevamiento_id}"


class Miembro(models.Model):
    relevamiento = models.ForeignKey(
        Relevamiento, on_delete=models.CASCADE, related_name="miembros")
    nombre = models.CharField(max_length=200)
    ci = models.CharField(max_length=100, blank=True)
    edad = models.IntegerField(null=True, blank=True)
    SEXO = [("M", "Masculino"), ("F", "Femenino")]
    sexo = models.CharField(max_length=1, choices=SEXO, blank=True)
    parentesco = models.CharField(max_length=100, blank=True)
    relacion_con_lote = models.CharField(max_length=200, blank=True)
    escolaridad = models.CharField(max_length=200, blank=True)
    grado_ano = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.nombre


class ProblemaSalud(models.Model):
    miembro = models.ForeignKey(
        Miembro, on_delete=models.CASCADE, related_name="problemas_salud")
    nombre = models.CharField(max_length=200)
    lugar_atencion = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.nombre} - {self.miembro.nombre}"


class OcupanteAnterior(models.Model):
    relevamiento = models.ForeignKey(
        Relevamiento, on_delete=models.CASCADE, related_name="ocupantes_anteriores")
    nombre_anterior = models.CharField(max_length=200, blank=True)
    ci_anterior = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.nombre_anterior or f"Anterior #{self.pk}"
