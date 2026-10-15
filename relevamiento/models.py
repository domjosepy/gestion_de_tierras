from django.db import models
from django.contrib.postgres.fields import ArrayField
import os
import re
from datetime import datetime
from django.db import transaction
from django.db.models import Max
from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# ============================
# FUNCIONES DE UTILIDAD PARA UPLOAD_TO
# ============================

def limpiar_nombre_carpeta(nombre):
    """
    Limpia un nombre de carpeta eliminando caracteres especiales y espacios.
    Convierte espacios a guiones bajos y elimina caracteres no alfanuméricos.
    """
    if not nombre:
        return 'sin_nombre'
    # Convertir a string y eliminar espacios al inicio/final
    nombre = str(nombre).strip()
    # Reemplazar espacios por guiones bajos
    nombre = nombre.replace(' ', '_')
    # Eliminar caracteres especiales, mantener solo alfanuméricos, guiones y guiones bajos
    nombre = re.sub(r'[^\w\-]', '', nombre)
    # Convertir a minúsculas para consistencia
    nombre = nombre.lower()
    return nombre or 'sin_nombre'


def path_relevamiento_upload(instance, filename):
    """
    Genera la ruta de subida para archivos generales de relevamiento.
    Estructura: relevamiento/{departamento}/{distrito}/{colonia}/{fecha_creacion_OT}/
    
    Args:
        instance: Instancia del modelo (debe tener relación con orden_trabajo)
        filename: Nombre del archivo original
        
    Returns:
        str: Ruta completa para guardar el archivo
    """
    try:
        # Obtener la orden de trabajo
        orden = instance.orden_trabajo
        
        # Obtener colonia y datos geográficos desde solicitud
        colonia = orden.solicitud.colonia if hasattr(orden, 'solicitud') else None
        distrito = colonia.distritos.first() if colonia else None
        departamento = distrito.departamento if distrito else None
        
        # Limpiar nombres de carpetas
        nombre_departamento = limpiar_nombre_carpeta(departamento.nombre if departamento else 'sin_departamento')
        nombre_distrito = limpiar_nombre_carpeta(distrito.nombre if distrito else 'sin_distrito')
        nombre_colonia = limpiar_nombre_carpeta(colonia.nombre if colonia else 'sin_colonia')
        
        # Formatear fecha de creación de la OT
        if orden.fecha_creacion:
            if isinstance(orden.fecha_creacion, datetime):
                fecha_carpeta = orden.fecha_creacion.strftime('%Y-%m-%d')
            else:
                fecha_carpeta = str(orden.fecha_creacion)[:10]  # Tomar solo la parte de fecha
        else:
            fecha_carpeta = 'sin_fecha'
        
        # Construir la ruta
        ruta = os.path.join(
            'relevamiento',
            nombre_departamento,
            nombre_distrito,
            nombre_colonia,
            fecha_carpeta,
            filename
        )
        
        return ruta
        
    except Exception as e:
        # En caso de error, usar una ruta por defecto
        print(f"Error al generar ruta de subida: {e}")
        return os.path.join('relevamiento', 'otros', filename)


def path_relevamiento_fotos_upload(instance, filename):
    """
    Genera la ruta de subida para fotos de encuestadores.
    Estructura: relevamiento/{departamento}/{distrito}/{colonia}/{fecha_creacion_OT}/FOTOS/
    
    Args:
        instance: Instancia del modelo (debe tener relación con orden_trabajo o relevamiento)
        filename: Nombre del archivo original
        
    Returns:
        str: Ruta completa para guardar el archivo
    """
    try:
        # Intentar obtener la orden de trabajo (puede venir de relevamiento u orden directa)
        if hasattr(instance, 'orden_trabajo'):
            orden = instance.orden_trabajo
        elif hasattr(instance, 'relevamiento'):
            orden = instance.relevamiento.orden_trabajo
        else:
            raise AttributeError("No se pudo obtener orden_trabajo")
        
        # Obtener colonia y datos geográficos desde solicitud
        colonia = orden.solicitud.colonia if hasattr(orden, 'solicitud') else None
        distrito = colonia.distritos.first() if colonia else None
        departamento = distrito.departamento if distrito else None
        
        # Limpiar nombres de carpetas
        nombre_departamento = limpiar_nombre_carpeta(departamento.nombre if departamento else 'sin_departamento')
        nombre_distrito = limpiar_nombre_carpeta(distrito.nombre if distrito else 'sin_distrito')
        nombre_colonia = limpiar_nombre_carpeta(colonia.nombre if colonia else 'sin_colonia')
        
        # Formatear fecha de creación de la OT
        if orden.fecha_creacion:
            if isinstance(orden.fecha_creacion, datetime):
                fecha_carpeta = orden.fecha_creacion.strftime('%Y-%m-%d')
            else:
                fecha_carpeta = str(orden.fecha_creacion)[:10]
        else:
            fecha_carpeta = 'sin_fecha'
        
        # Construir la ruta con subcarpeta FOTOS
        ruta = os.path.join(
            'relevamiento',
            nombre_departamento,
            nombre_distrito,
            nombre_colonia,
            fecha_carpeta,
            'FOTOS',
            filename
        )
        
        return ruta
        
    except Exception as e:
        # En caso de error, usar una ruta por defecto
        print(f"Error al generar ruta de fotos: {e}")
        return os.path.join('relevamiento', 'otros', 'FOTOS', filename)


# ============================
# CHOICES
# ============================

# ver si se puede automatizar el check, por ej. registro es igual a REGISTRO-
USO_LOTE_OCUPANTE_CHOICES = [
    ("agropecuario_forestal", "Agropecuario/Forestal"), ("forestal_nativa", "Forestal - Nativa"),
    ("forestal_reforestado", "Forestal - Reforestado"), ("barbecho_descanso", "Barbecho - Descanso"),
    ("abandonado", "Abandonado"), ("comercial", "Comercial"), ("sitio_vacio", "Sitio Vacío"), 
]

USO_LOTE_SERVICIO_CHOICES = [
    ("abandonado", "Abandonado"), ("comercial", "Comercial"), ("industrial", "Industrial"),
    ("local_politico", "Local Político"), ("local_recreativo", "Local Recreativo"),
    ("local_religioso", "Local Religioso"), ("sitio_vacio", "Sitio Vacío"), 
    ("institucion_organizacion", "Institución/Organización"),
]


MEJORAS_CHOICES = [
    ("galpon", "Galpón"), ("corrales", "Corrales"), ("bretes", "Bretes"), ("represa", "Represa"),
    ("sanitarios", "Instalaciones Sanitarias"), ("pozo", "Pozo"), ("tajamares", "Tajamares"),
    ("mangas", "Mangas"), ("cercado_perimetral", "Cercado Perimetral"), ("silos", "Silos"),
    ("canales_riego", "Canales de Irrigación"), ("energia_electrica", "Energía Eléctrica"),
    ("agua_potable", "Agua Potable"),
]

EQUIPAMIENTOS_CHOICES = [
    ("energia_electrica", "Energía Eléctrica"), ("agua_corriente", "Agua Corriente"),
    ("cocina", "Cocina"), ("heladera", "Heladera"), ("lavadora", "Lavadora"), ("bano", "Baño"), 
    ("computadora", "Computadora"), ("internet", "Internet"), ("television", "Televisión"), ("radio", "Radio"), 
    ("telefono_fijo", "Teléfono Fijo"),
    ("vehiculo", "Vehículo"), ("motocicleta", "Motocicleta"),("bicicleta", "Bicicleta"),("tractor", "Tractor"),
    ("camion", "Camión"),

]

MODIFICACIONES_POSTADJUDICACION_CHOICES = [
    ("cambio_recurrente", "Cambio de Recurrente"),
    ("correccion_superficie", "Corrección de Superficie"),
    ("ampliacion", "Ampliación"),
]

COND_VIVIENDA_CHOICES = [
    ("presente", "Presente"),
    ("ausente", "Ausente"),
    ("sin_vivienda", "Sin vivienda"),
    ("servicio", "Servicio"),
    ("en_construccion", "En construcción"),
    ("desocupada", "Desocupada")
]

ESTADO_CIVIL_CHOICES = [
    ("soltero", "Soltero/a"),
    ("casado", "Casado/a"),
    ("concubino", "Concubino/a"),
    ("divorciado", "Divorciado/a"),
    ("viudo", "Viudo/a"),
]

# Tipo de registro del formulario (define el flujo/wizard a seguir)
TIPO_REGISTRO_CHOICES = [
    ("ocupante", "Ocupante"),
    ("conflicto", "Conflicto"),
    ("servicio", "Servicio"),
    ("fraccionamiento", "Fraccionamiento"),
]

TIPO_CULTIVO_CHOICES = [
    ("algodon", "Algodón"), ("arroz", "Arroz"), ("banano", "Banano"), ("cana_dulce", "Caña de azúcar"), ("canola", "Canola"),
    ("cebolla", "Cebolla"), ("citricos", "Cítricos (naranja, limón, etc.)"), ("forestal", "Forestal (eucalipto, pino, etc.)"), 
    ("forrajeras", "Forrajeras (pastura)"), ("girasol", "Girasol"), ("legumbre_batata", "Legumbre / Batata"), ("locote", "Locote"),
    ("maiz_chipa", "Maíz Chipá"), ("maiz_tupi", "Maíz Tupí"), ("mandioca", "Mandioca"), ("mango", "Mango"), ("mani", "Maní"),
    ("melon", "Melón"), ("pina", "Piña"), ("poroto", "Poroto"), ("sandia", "Sandía"), ("sesamo", "Sésamo"), ("soja", "Soja"),
    ("tomate", "Tomate"), ("trigo", "Trigo"), ("yerba_mate", "Yerba Mate"), ("zapallo", "Zapallo"), ("otro", "Otro"),
]


TIPO_GANADERIA_CHOICES = [
    ("bovinos", "Bovinos"), ("porcinos", "Porcinos"), ("aves", "Aves"), ("caprinos", "Caprinos"),
    ("ovinos", "Ovinos"), ("equinos", "Equinos"), ("conejos", "Conejos"), ("patos", "Patos"), 
    ("pavos", "Pavos"), ("otros", "Otros"),
]


class Relevamiento(models.Model):

    # 1 - DATOS GEOGRAFICOS
    departamento = models.ForeignKey(
        "core.Departamento", on_delete=models.PROTECT, null=True, blank=True)
    distrito = models.ForeignKey(
        "core.Distrito", on_delete=models.PROTECT, null=True, blank=True)
    colonia = models.ForeignKey(
        "core.Colonia", on_delete=models.PROTECT, null=True, blank=True)
    # DATOS DEL LOTE
    manzana = models.CharField(max_length=50, blank=True)
    lote_indert = models.CharField(max_length=50, blank=True)
    lote_sirt = models.CharField(max_length=50, blank=True)
    frente_aprox = models.PositiveIntegerField(null=True, blank=True, verbose_name="Frente aproximado (m)")
    fondo_aprox = models.PositiveIntegerField(null=True, blank=True, verbose_name="Fondo aproximado (m)")
    formulario = models.IntegerField(null=True, blank=True, auto_created=True)
    observacion_encuesta = models.TextField(blank=True)

    #id compuesto por id del departamento, distrito, colonia, manzana y lote_indert
    id_relevamiento = models.CharField(max_length=255, editable=False, blank=True, null=True)
    # Tipo de registro: define el flujo (Ocupante/Conflicto/Servicio/Fraccionamiento)
    tipo_registro = models.CharField(
        max_length=20, choices=TIPO_REGISTRO_CHOICES, default="ocupante",
        verbose_name="Tipo de Registro")

    uso_lote_ocupante = ArrayField(
        base_field=models.CharField(max_length=50, choices=USO_LOTE_OCUPANTE_CHOICES),
        blank=True,
        null=True,
        default=list,
    )
    uso_lote_servicio = ArrayField(
            base_field=models.CharField(max_length=50, choices=USO_LOTE_SERVICIO_CHOICES),
            blank=True,
            null=True,
            default=list,
        )

    # 2 - DATOS DE LA OCUPACIÓN
    TIPO_LOTE_CHOICES = [("agricola", "Agrícola"),
                         ("quinta", "Quinta"), ("urbano", "Urbano")]

    tipo_lote = models.CharField(
        max_length=20, choices=TIPO_LOTE_CHOICES, blank=True)
    
    superficie_ha = models.FloatField(null=True, blank=True)
    dimensiones = models.CharField(max_length=200, blank=True)
    vive_en_lote = models.BooleanField(default=False)
    condicion_vivienda = models.CharField(
        max_length=20, choices=COND_VIVIENDA_CHOICES, default="sin_vivienda")


    COND_ENCUESTADO_CHOICES = [
        ("titular", "Titular"),
        ("ocupante", "Ocupante"),
        ("pariente", "Pariente o no pariente"),
        ("otro", "Otro"),
    ]

    condicion_encuestado = models.CharField(
        max_length=20, choices=COND_ENCUESTADO_CHOICES, default="ocupante")

    # ── Progreso del wizard ──────────────────────────────────────────────
    ESTADO_CARGA_CHOICES = [
        ("parte_1", "Datos geográficos y ocupante"),
        ("parte_2", "Datos del lote"),
        ("parte_3", "Vivienda / Datos productivos"),
        ("parte_4", "Información de encuesta"),
        ("completo", "Completo"),
    ]
    estado_carga = models.CharField(
        max_length=20, choices=ESTADO_CARGA_CHOICES, default="parte_1",
        verbose_name="Estado de carga"
    )

    # ── Datos del ocupante ───────────────────────────────────────────────
    quien_es_el_ocupante = models.CharField(max_length=200, blank=True)
    cedula_ocupante = models.CharField(
        max_length=8,
        blank=True, null=True
    )
    sexo_ocupante = models.CharField(max_length=1, choices=[("M", "Masculino"), ("F", "Femenino")], blank=True)
    estado_civil_ocupante = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, blank=True)

    # Datos del conyuge
    quien_es_el_conyuge = models.CharField(max_length=200, blank=True)
    cedula_conyuge = models.CharField(max_length=8,blank=True, null=True)
    sexo_conyuge = models.CharField(max_length=1, choices=[("M", "Masculino"), ("F", "Femenino")], blank=True)
    estado_civil_conyuge = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, blank=True)
           

    # Si no vive en el lote: datos de residencia
    residencia_manzana = models.CharField(max_length=50, blank=True)
    residencia_lote = models.CharField(max_length=50, blank=True)
    parentesco = models.CharField(max_length=200, blank=True)
    encargado_residencia = models.CharField(max_length=200, blank=True)

    # 4 - USO DE LA TIERRA Y MEJORAS
    produccion_agricola_ha = models.FloatField(default=0, blank=True)
    produccion_ganadera_ha = models.FloatField(default=0, blank=True)
    reforestado_ha = models.FloatField(default=0, blank=True)
    bosque_natural_ha = models.FloatField(default=0, blank=True)
    barbecho_ha = models.FloatField(default=0, blank=True)

    parent_lote = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_lotes',
        verbose_name="Lote padre (si es sub-lote)"
    )

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
        base_field=models.CharField(max_length=50, choices=MODIFICACIONES_POSTADJUDICACION_CHOICES),
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

    # Archivo comprimido subido por el subcoordinador
    archivo_subcoordinador = models.FileField(
        upload_to=path_relevamiento_upload,
        blank=True,
        null=True,
        verbose_name="Archivo del Subcoordinador",
        help_text="Archivo comprimido (.zip, .rar, .7z, etc.) - Se organiza en: relevamiento/{depto}/{distrito}/{colonia}/{fecha_OT}/"
    )
    fecha_subida_archivo = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Subida del Archivo"
    )

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    fecha_de_encuesta = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha y hora de la encuesta",
        help_text="Se completa automáticamente al confirmar y finalizar el relevamiento."
    )
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["departamento", "distrito", "colonia", "manzana", "lote_indert"],
                name="unique_relevamiento"
            )
        ]
    
    def __str__(self):
        return f"Relevamiento #{self.pk} - {self.colonia or 'sin colonia'}"

    def save(self, *args, **kwargs):
        # Generamos el id compuesto por id del departamento, distrito, colonia, manzana y lote_indert
        if self.departamento and self.distrito and self.colonia and self.manzana and self.lote_indert:
            self.id_relevamiento = f"{self.departamento}-{self.distrito}-{self.colonia}-{self.manzana}_{self.lote_indert}"

        #Guardamos lote_sirt igual a lote indert
        if self.lote_indert:
            self.lote_sirt = self.lote_indert

        #Guardamos los campos quien_es_el_ocupante y quien_es_el_conyuge en mayúsculas
        if self.quien_es_el_ocupante:
            self.quien_es_el_ocupante = self.quien_es_el_ocupante.upper()
        if self.quien_es_el_conyuge:
            self.quien_es_el_conyuge = self.quien_es_el_conyuge.upper()

        # Guardamos observaciones de relevamiento en mayúsculas
        if self.observacion_encuesta:
            self.observacion_encuesta = self.observacion_encuesta.upper()
            
        # Si el tipo de registro es "servicio", se establece la condición de vivienda como "servicio"
        if self.tipo_registro == "servicio":
            self.condicion_vivienda = "servicio"

        """
        Auto-asigna el campo `formulario` de forma incremental por `orden_trabajo`.
        Se usa bloqueo transaccional sobre la fila de `OrdenTrabajo` para evitar
        condiciones de carrera cuando se crean relevamientos concurrentes.
        """

        # Solo asignar si no está definido y existe orden_trabajo
        if (self.formulario is None or self.formulario == '') and getattr(self, 'orden_trabajo_id', None):
            with transaction.atomic():
                # Bloquear la fila de OrdenTrabajo para esta orden
                OrdenTrabajo = apps.get_model('coordinacion', 'OrdenTrabajo')
                OrdenTrabajo.objects.select_for_update().get(pk=self.orden_trabajo_id)

                # Calcular el máximo formulario actual y asignar siguiente número
                last = Relevamiento.objects.filter(
                    orden_trabajo_id=self.orden_trabajo_id
                ).aggregate(m=Max('formulario'))['m']
                self.formulario = 1 if last is None else (last + 1)

        super().save(*args, **kwargs)

    def siguiente_sufijo_sublote(self):
        """Siguiente letra secuencial (A, B, C...) para el próximo sub-lote de fraccionamiento."""
        existentes = self.sub_lotes.count()
        return chr(ord('A') + existentes)


class Pretendiente(models.Model):
    """Representa a cada reclamante en un lote en conflicto."""
    relevamiento = models.ForeignKey(
        Relevamiento,
        on_delete=models.CASCADE,
        related_name='pretendientes'
    )
    nombre_pretendiente = models.CharField(max_length=200)
    ci_pretendiente = models.CharField(max_length=100, blank=True)
    sexo_pretendiente = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Femenino')], blank=True)
    estado_civil_pretendiente = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, blank=True)
    condicion_vivienda = models.CharField(max_length=20, choices=COND_VIVIENDA_CHOICES, blank=True)
    vive_en_lote = models.BooleanField(default=False)
    residencia_manzana = models.CharField(max_length=50, blank=True)
    residencia_lote = models.CharField(max_length=50, blank=True)
    quien_es_el_ocupante = models.CharField(max_length=200, blank=True)
    parentesco = models.CharField(max_length=200, blank=True)

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

    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f"{self.nombre_pretendiente} (Pretendiente)"


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
        upload_to=path_relevamiento_fotos_upload,
        blank=True,
        null=True,
        help_text="Se guardará en: relevamiento/{depto}/{distrito}/{colonia}/{fecha_OT}/FOTOS/"
    )
    nombre_archivo = models.CharField(max_length=255, blank=True)
    pretendiente = models.ForeignKey(
        'Pretendiente',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='documentos'
    )

    def __str__(self):
        return f"{self.tipo} - {self.nombre_archivo or (self.archivo.name if self.archivo else '')}"


class Cultivo(models.Model):
    TIPO_SIEMBRA = [("temporal", "Temporal"), ("permanente", "Permanente")]
    relevamiento = models.ForeignKey(
        Relevamiento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cultivos"
    )
    pretendiente = models.ForeignKey(
        'Pretendiente',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cultivos'
    )
    tipo_cultivo = models.CharField(max_length=50, choices=TIPO_CULTIVO_CHOICES)
    tipo_siembra = models.CharField(max_length=20, choices=TIPO_SIEMBRA, blank=True)
    hectareas = models.FloatField()

    def __str__(self):
        return f"{self.get_tipo_cultivo_display()} ({self.hectareas} Ha)"


class ProduccionGanadera(models.Model):
    relevamiento = models.ForeignKey(
        Relevamiento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="producciones_ganaderas"
    )
    pretendiente = models.ForeignKey(
        'Pretendiente',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='producciones_ganaderas'
    )
    tipo_ganaderia = models.CharField(max_length=50, choices=TIPO_GANADERIA_CHOICES)
    cantidad = models.IntegerField()

    def __str__(self):
        return f"{self.get_tipo_ganaderia_display()} x {self.cantidad}"


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

    relevamiento = models.ForeignKey(
        Relevamiento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='viviendas'
    )
    pretendiente = models.ForeignKey(
        'Pretendiente',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='viviendas'
    )
    es_principal = models.BooleanField(default=False, verbose_name="Es vivienda principal")
    numero = models.PositiveSmallIntegerField(default=1, verbose_name="Número de vivienda")
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

    def clean(self):
        # Ya NO validamos acá. Esto corría en cada is_valid() del formset,
        # incluso cuando el Relevamiento/Pretendiente padre todavía no
        # existía (se crea en el mismo POST, después de la validación).
        # La validación real se hace en save() — ver abajo — que sí se
        # ejecuta en el momento correcto, después de asignar la FK real.
        pass

    def save(self, *args, **kwargs):
        if not self.relevamiento_id and not self.pretendiente_id:
            raise ValidationError("La vivienda debe estar asociada a un relevamiento o a un pretendiente.")
        super().save(*args, **kwargs)

    def __str__(self):
        owner = self.relevamiento or self.pretendiente
        return f"Vivienda #{self.numero} — {owner}"

# MANEJO DE MIEMBROS DE LA FAMILIA / POBLACION
class Miembro(models.Model):
    relevamiento = models.ForeignKey(
        Relevamiento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="miembros"
    )
    vivienda = models.ForeignKey(
        'Vivienda',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='miembros'
    )
    pretendiente = models.ForeignKey(
        'Pretendiente',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='miembros'
    )
    nombre_miembro = models.CharField(max_length=200)
    ci_miembro = models.CharField(max_length=100, blank=True)
    edad_miembro = models.IntegerField(null=True, blank=True)
    SEXO = [("M", "Masculino"), ("F", "Femenino")]
    sexo_miembro = models.CharField(max_length=1, choices=SEXO, blank=True)
    estado_civil_miembro = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, blank=True)
    parentesco = models.CharField(max_length=100, blank=True)
    relacion_con_lote = models.CharField(max_length=200, blank=True)
    escolaridad = models.CharField(max_length=200, blank=True)
    grado_ano = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.nombre_miembro


class ProblemaSalud(models.Model):
    miembro = models.ForeignKey(
        Miembro, on_delete=models.CASCADE, related_name="problemas_salud")
    nombre = models.CharField(max_length=200)
    lugar_atencion = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.nombre_miembro} - {self.miembro.nombre_miembro}"


class OcupanteAnterior(models.Model):
    relevamiento = models.ForeignKey(
        Relevamiento, on_delete=models.CASCADE, related_name="ocupantes_anteriores")
    nombre_anterior = models.CharField(max_length=200, blank=True)
    ci_anterior = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.nombre_anterior or f"Anterior #{self.pk}"


class FotoRelevamiento(models.Model):
    """
    Modelo para almacenar fotos tomadas durante el relevamiento.
    Las fotos se organizan automáticamente en carpetas por departamento/distrito/colonia/fecha.
    """
    TIPO_FOTO_CHOICES = [
        ('vivienda_frente', 'Vivienda - Frente'),
        ('vivienda_lateral', 'Vivienda - Lateral'),
        ('vivienda_fondo', 'Vivienda - Fondo'),
        ('lote_general', 'Vista General del Lote'),
        ('mejoras', 'Mejoras/Construcciones'),
        ('cultivos', 'Cultivos'),
        ('documento', 'Documento/Título'),
        ('familia', 'Familia'),
        ('otro', 'Otro'),
    ]
    
    relevamiento = models.ForeignKey(
        Relevamiento,
        on_delete=models.CASCADE,
        related_name='fotos',
        verbose_name="Relevamiento"
    )
    foto = models.ImageField(
        upload_to=path_relevamiento_fotos_upload,
        verbose_name="Fotografía",
        help_text="Se guardará en: relevamiento/{depto}/{distrito}/{colonia}/{fecha_OT}/FOTOS/"
    )
    tipo_foto = models.CharField(
        max_length=30,
        choices=TIPO_FOTO_CHOICES,
        default='otro',
        verbose_name="Tipo de Foto"
    )
    descripcion = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Descripción"
    )
    encuestador = models.ForeignKey(
        'administrador.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fotos_tomadas',
        verbose_name="Encuestador"
    )
    vivienda = models.ForeignKey(
        'Vivienda',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fotos'
    )
    fecha_captura = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Captura"
    )
    latitud = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="Latitud",
        help_text="Coordenada GPS de la foto"
    )
    longitud = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True,
        verbose_name="Longitud",
        help_text="Coordenada GPS de la foto"
    )
    
    class Meta:
        verbose_name = "Foto de Relevamiento"
        verbose_name_plural = "Fotos de Relevamiento"
        ordering = ['-fecha_captura']
    
    def __str__(self):
        return f"{self.get_tipo_foto_display()} - {self.relevamiento}"




class InstitucionEnLote(models.Model):
    """Institución u organización ubicada dentro del lote de un ocupante o pretendiente."""
    relevamiento = models.ForeignKey(
        Relevamiento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='instituciones'
    )
    pretendiente = models.ForeignKey(
        'Pretendiente',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='instituciones'
    )
    nombre_servicio = models.CharField(max_length=200)
    ruc_servicio = models.CharField(max_length=50, blank=True)
    descripcion_servicio = models.TextField(blank=True)

    def clean(self):
        if not self.relevamiento_id and not self.pretendiente_id:
            raise ValidationError("La institución debe estar asociada a un relevamiento o a un pretendiente.")

    def __str__(self):
        return self.nombre_servicio


### SUBCOORDINADOR
class ArchivoSubcoordinador(models.Model):
    """Modelo para registrar archivos comprimidos subidos por subcoordinadores."""
    orden_trabajo = models.ForeignKey(
        'coordinacion.OrdenTrabajo',
        on_delete=models.CASCADE,
        related_name='archivos_subcoordinador',
        verbose_name="Orden de Trabajo"
    )
    archivo = models.FileField(
        upload_to=path_relevamiento_upload,
        verbose_name="Archivo Comprimido",
        help_text="Se organizará automáticamente en: relevamiento/{depto}/{distrito}/{colonia}/{fecha_OT}/"
    )
    nombre_archivo = models.CharField(
        max_length=255,
        verbose_name="Nombre del Archivo"
    )
    subido_por = models.ForeignKey(
        'administrador.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='archivos_subidos',
        verbose_name="Subido por"
    )
    fecha_subida = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Subida"
    )
    
    class Meta:
        verbose_name = "Archivo de Subcoordinador"
        verbose_name_plural = "Archivos de Subcoordinadores"
        ordering = ['-fecha_subida']
    
    def __str__(self):
        return f"{self.nombre_archivo} - {self.fecha_subida.strftime('%d/%m/%Y')}"


