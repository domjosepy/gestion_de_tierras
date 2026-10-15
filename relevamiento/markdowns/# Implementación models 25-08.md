# Documento de Implementación para Formulario de Relevamiento

**Versión:** 1.1  
**Fecha:** 2026-08-25  
**Autor:** Equipo de Desarrollo

---

## 1. Resumen de Decisiones

Tras el análisis del formulario y los modelos existentes, se acordaron las siguientes decisiones:

- **Modo Ocupante** sigue utilizando `Relevamiento` como contenedor principal de los datos del ocupante. No se crea un modelo separado para el ocupante único.
- **Modo Conflicto** utiliza un nuevo modelo `Pretendiente` para cada reclamante del lote. Cada pretendiente tendrá sus propios datos personales, productivos, vivienda y población.
- **Miembros** (población) estarán asociados a una `Vivienda` (obligatorio) y opcionalmente a `Relevamiento` o `Pretendiente` para facilitar consultas rápidas y mantener coherencia.
- **Fotos de viviendas** adicionales se gestionarán a través del modelo existente `FotoRelevamiento`, agregando un campo `vivienda` (ForeignKey) para vincular la foto a una vivienda específica.
- **Documentos** podrán estar asociados tanto a `Relevamiento` como a `Pretendiente`, agregando un FK opcional a este último.
- **Modo Servicio** se mantiene como un `Relevamiento` con `uso_lote = "institucion_organizacion"` y sin población. Adicionalmente, dentro de un lote de ocupante o pretendiente puede existir una institución (p. ej., puesto de salud, escuela), para lo cual se creará un modelo `InstitucionEnLote` que capturará nombre, RUC y descripción, asociado al `Relevamiento` o `Pretendiente` correspondiente.
- **Fraccionamiento** se representa mediante `Relevamiento` padre y sub‑lotes (`Relevamiento` hijos) con un campo `parent_lote` (self FK). Cada sub‑lote se trata como un ocupante independiente.
- El **cónyuge** se guardará como un `Miembro` con parentesco "Cónyuge", generado automáticamente si se cargan sus datos en el formulario.
- **Cultivos** y **Producción Ganadera** se manejan como tablas dinámicas: el encuestador selecciona de una lista predefinida el tipo de cultivo o ganado, e ingresa la superficie sembrada (Ha) o cantidad de animales respectivamente.

---

## 2. Modelos Existentes: Modificaciones Requeridas

### 2.1. `Relevamiento`

Se deben realizar los siguientes cambios:

- Agregar `"en_construccion"` a `COND_VIVIENDA_CHOICES`.
- Agregar campo `parent_lote` (self ForeignKey) para fraccionamiento:
  ```python
  parent_lote = models.ForeignKey(
      'self',
      on_delete=models.CASCADE,
      null=True,
      blank=True,
      related_name='sub_lotes',
      verbose_name="Lote padre (si es sub-lote)"
  )
    ```
- Opcional: agregar campo sublote_letra para guardar la letra (A, B, …) si se desea mostrar explícitamente.

- Nota: Se mantiene condicion_vivienda con la opción "servicio" para el modo Servicio puro.

### 2.2. `Vivienda`
- Cambios necesarios para soportar múltiples viviendas por lote y viviendas de pretendientes:
- Eliminar OneToOneField a Relevamiento y reemplazarlo por dos FKs opcionales:
``` python

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
```
- Agregar es_principal (BooleanField, default=False) para identificar la vivienda principal del ocupante/pretendiente.
- Agregar numero (PositiveSmallIntegerField, default=1) para ordenar viviendas adicionales.

### 2.3. `Miembro`
- Se flexibiliza la relación con vivienda:
- Eliminar el ForeignKey directo a Relevamiento (o mantenerlo opcional) y agregar:
```python
vivienda = models.ForeignKey(
    Vivienda,
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
```
- relevamiento puede quedar como campo opcional para consultas rápidas, pero la asociación principal será a través de vivienda.

### 2.4. `Cultivo`
- Se convierte en una tabla de selección múltiple con superficie por tipo de cultivo.
- Cambios:
- Reemplazar el campo descripcion por una clave tipo_cultivo (CharField con choices) que contenga los cultivos más comunes de Paraguay.
- Mantener tipo_siembra (temporal/permanente) como campo opcional para indicar el ciclo.
- Mantener hectareas como FloatField para la superficie sembrada.
- Agregar FK opcional a Pretendiente:
```python
pretendiente = models.ForeignKey(
    'Pretendiente',
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name='cultivos'
)
```
- relevamiento sigue existiendo para el modo ocupante/fraccionamiento.

### 2.4. `Cultivo`
- Se convierte en una tabla de selección múltiple con superficie por tipo de cultivo.

- Cambios:
- Reemplazar el campo descripcion por una clave tipo_cultivo (CharField con choices) que contenga los cultivos más comunes de Paraguay.
- Mantener tipo_siembra (temporal/permanente) como campo opcional para indicar el ciclo.
- Mantener hectareas como FloatField para la superficie sembrada.
- Agregar FK opcional a Pretendiente:
```python
pretendiente = models.ForeignKey(
    'Pretendiente',
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name='cultivos'
)
```
- relevamiento sigue existiendo para el modo ocupante/fraccionamiento.
# 🌱 Lista de Cultivos Agrícolas

| Clave           | Nombre común                       |
|-----------------|------------------------------------|
| maiz_tupi       | Maíz Tupí                          |
| maiz_chipa      | Maíz Chipá                         |
| mandioca        | Mandioca                           |
| poroto          | Poroto                             |
| arroz           | Arroz                              |
| legumbre_batata | Legumbre / Batata                  |
| soja            | Soja                               |
| trigo           | Trigo                              |
| girasol         | Girasol                            |
| canola          | Canola                             |
| sésamo          | Sésamo                             |
| mani            | Maní                               |
| caña_dulce      | Caña de azúcar                     |
| algodon         | Algodón                            |
| yerba_mate      | Yerba Mate                         |
| citricos        | Cítricos (naranja, limón, etc.)    |
| banano          | Banano                             |
| piña            | Piña                               |
| mango           | Mango                              |
| papa            | Papa                               |
| cebolla         | Cebolla                            |
| tomate          | Tomate                             |
| locote          | Locote                             |
| zapallo         | Zapallo                            |
| sandia          | Sandía                             |
| melón           | Melón                              |
| forrajeras      | Forrajeras (pastura)               |
| forestal        | Forestal (eucalipto, pino, etc.)   |
| otro            | Otro                               |

---
### 2.5. `ProduccionGanadera`
- Se convierte en una tabla de selección múltiple con cantidad por tipo de animal.

- Cambios:
- Reemplazar descripcion por tipo_ganado (CharField con choices) con las especies más comunes.
- Mantener cantidad como IntegerField.
- Agregar FK opcional a Pretendiente:
```python
pretendiente = models.ForeignKey(
    'Pretendiente',
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name='producciones_ganaderas'
)
```
# 🐄 Lista de Producción Ganadera

| Clave     | Nombre común                |
|-----------|-----------------------------|
| bovinos   | Bovinos (vacas, toros)      |
| porcinos  | Porcinos (cerdos)           |
| aves      | Aves (pollos, gallinas)     |
| caprinos  | Caprinos (cabras)           |
| ovinos    | Ovinos (ovejas)             |
| equinos   | Equinos (caballos)          |
| bubalinos | Bubalinos (búfalos)         |
| conejos   | Conejos                      |
| patos     | Patos                        |
| pavos     | Pavos                        |
| otros     | Otros                        |


### 2.6. `FotoRelevamiento`
- Agregar FK opcional a Vivienda:
```python
vivienda = models.ForeignKey(
    Vivienda,
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name='fotos'
)
```
relevamiento se mantiene para fotos generales del lote.

### 2.7. `Documento`
- Agregar FK opcional a Pretendiente:

```python
pretendiente = models.ForeignKey(
    'Pretendiente',
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name='documentos'
)
```

## 3. Nuevos Modelos a Crear

### 3.1. `Pretendiente`
- Representa a cada reclamante en un lote en conflicto.
``` python
class Pretendiente(models.Model):
    relevamiento = models.ForeignKey(
        Relevamiento,
        on_delete=models.CASCADE,
        related_name='pretendientes'
    )
    nombre = models.CharField(max_length=200)
    ci = models.CharField(max_length=100, blank=True)
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Femenino')], blank=True)
    estado_civil = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, blank=True)
    condicion_vivienda = models.CharField(
        max_length=20,
        choices=COND_VIVIENDA_CHOICES,  # incluye 'en_construccion'
        blank=True
    )
    vive_en_lote = models.BooleanField(default=False)
    residencia_manzana = models.CharField(max_length=50, blank=True)
    residencia_lote = models.CharField(max_length=50, blank=True)
    quien_es_el_ocupante = models.CharField(max_length=200, blank=True)
    parentesco = models.CharField(max_length=200, blank=True)

    # Datos productivos
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
        return f"{self.nombre} (Pretendiente)"
```

### 3.2. `InstitucionEnLote`
- Permite registrar una institución u organización que se encuentre dentro del lote de un ocupante o pretendiente (no es el lote completo, sino una parte).

``` python
class InstitucionEnLote(models.Model):
    relevamiento = models.ForeignKey(
        Relevamiento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='instituciones'
    )
    pretendiente = models.ForeignKey(
        Pretendiente,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='instituciones'
    )
    nombre = models.CharField(max_length=200)
    ruc = models.CharField(max_length=50, blank=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre
```
- Nota: Se debe validar que al menos uno de relevamiento o pretendiente esté definido.

## 4. Relaciones y Diagrama Conceptual

A continuación se describen las relaciones principales:

### Relevamiento (lote)
- Puede tener:
  - Muchas **Vivienda** (principal y adicionales).
  - Muchos **Miembro** (a través de las viviendas o directamente).
  - Muchos **Pretendiente** (si es conflicto).
  - Muchas **InstitucionEnLote**.
  - Muchos **Documento**.
  - Muchos **Cultivo** y **ProduccionGanadera** (si no es conflicto).
  - Muchas **FotoRelevamiento**.
  - **Sub‑lotes** (Relevamiento hijos con `parent_lote`).

### Pretendiente
- Puede tener:
  - Muchas **Vivienda**.
  - Muchos **Miembro** (a través de viviendas).
  - Muchos **Cultivo** y **ProduccionGanadera**.
  - Muchas **InstitucionEnLote**.
  - Muchos **Documento**.

### Vivienda
- Puede tener:
  - Muchos **Miembro**.
  - Muchas **FotoRelevamiento**.


## 5. Flujo del Formulario y Persistencia

### 5.1. Modo Ocupante
- Se crea un **Relevamiento** con los datos geográficos, del lote y del ocupante principal.
- Según `condicion_vivienda`:
  - **presente** o **ausente** → se registran características/equipamiento de la vivienda principal.
  - **en_construccion** → solo características.
  - **sin_vivienda** → se solicita información de residencia.
- Se crea la **Vivienda principal** (`es_principal=True`) y se asocia al Relevamiento.
- Se agregan los **Miembro** (incluyendo al ocupante como *Jefe de hogar* y al cónyuge si se cargó).
- Se registran **Cultivo** y **ProduccionGanadera** vinculados al Relevamiento.
- Si dentro del lote existe una institución, se crea una **InstitucionEnLote** con los datos capturados.
- Si hay viviendas adicionales (*solo vivienda*), se crean nuevas **Vivienda** (`es_principal=False`), cada una con su propia población (**Miembro**) y fotos si se tomaron.

### 5.2. Modo Conflicto
- Se crea un **Relevamiento** con estado `en_conflicto` y sin datos de ocupante único.
- Por cada **Pretendiente** se crea un registro asociado al Relevamiento.
- Para cada Pretendiente:
  - Según su `condicion_vivienda`, se crea una o más **Vivienda** (principal y adicionales).
  - Se cargan sus **Miembro**.
  - Cada pretendiente puede tener sus propios **Cultivo**, **ProduccionGanadera**, **Documento** e **InstitucionEnLote**.
- Las fotos de viviendas se asocian a la **Vivienda** correspondiente del pretendiente.

### 5.3. Modo Servicio
- Se crea un **Relevamiento** con `uso_lote = "institucion_organizacion"` y `condicion_vivienda = "servicio"` (o vacío).
- No se crean **Vivienda** ni **Miembro**.
- Los datos específicos (nombre, RUC, descripción) se almacenan en **InstitucionEnLote** asociada al Relevamiento (aunque el lote entero sea la institución).

### 5.4. Modo Fraccionamiento
- Se crea un **Relevamiento padre** (lote original).
- Al pulsar *Realizar fraccionamiento*, se crea un nuevo **Relevamiento hijo** con `parent_lote` apuntando al padre y con los datos del sub‑lote (manzana, lote_indert con letra, superficie, etc.).
- El sub‑lote se comporta como un ocupante normal: se le asigna su vivienda, miembros, cultivos, etc.

## 6. Consideraciones de Migración
- Los cambios en **Vivienda**, **Miembro**, **Cultivo**, etc., implican modificar las relaciones existentes.
- Se deberá crear **migraciones de Django** y posiblemente migraciones de datos si ya hay registros en producción.
- Para **Vivienda**, la migración debe:
  - Eliminar la restricción *OneToOne*.
  - Agregar los nuevos campos.
  - Recomendación: hacerlo en pasos → primero agregar campos, luego migrar datos (si es necesario), y finalmente eliminar el campo antiguo.
- Se debe añadir validación en `clean()` de **Vivienda** y **InstitucionEnLote** para garantizar que al menos uno de los FKs (`relevamiento` o `pretendiente`) esté presente.

## 7. Próximos Pasos
- Implementar los cambios en `models.py`.
- Generar y aplicar migraciones.
- Ajustar el frontend para enviar los datos estructurados según el nuevo esquema.
- Crear **serializers** (si se usa DRF) y vistas para manejar la creación/edición de los diferentes modos.
- Probar con datos reales.
