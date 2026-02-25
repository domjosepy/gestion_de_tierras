from django.db import models
from django.contrib.postgres.fields import ArrayField
import os
import re
from datetime import datetime

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
        upload_to=path_relevamiento_fotos_upload,
        blank=True,
        null=True,
        help_text="Se guardará en: relevamiento/{depto}/{distrito}/{colonia}/{fecha_OT}/FOTOS/"
    )
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
