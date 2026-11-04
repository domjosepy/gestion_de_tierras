# Estructura de Carpetas para Archivos de Relevamiento

## 📁 Descripción General

Este documento explica cómo funciona la organización automática de archivos en el sistema de relevamiento.

Los archivos se organizan automáticamente en carpetas basadas en la ubicación geográfica y fecha de creación de la Orden de Trabajo.

---

## 🗂️ Estructura de Carpetas

### Archivos Generales
```
media/
└── relevamiento/
    └── {departamento}/
        └── {distrito}/
            └── {colonia}/
                └── {fecha_creacion_OT}/
                    ├── archivo1.zip
                    ├── archivo2.rar
                    └── documento.pdf
```

### Fotos de Encuestadores
```
media/
└── relevamiento/
    └── {departamento}/
        └── {distrito}/
            └── {colonia}/
                └── {fecha_creacion_OT}/
                    └── FOTOS/
                        ├── foto1.jpg
                        ├── foto2.png
                        └── foto3.jpg
```

---

## 🔧 Funciones Implementadas

### 1. `limpiar_nombre_carpeta(nombre)`
**Propósito:** Limpia nombres de carpetas para evitar caracteres problemáticos en el sistema de archivos.

**Procesamiento:**
- Elimina espacios al inicio/final
- Convierte espacios a guiones bajos (`_`)
- Elimina caracteres especiales (mantiene solo alfanuméricos, `-` y `_`)
- Convierte a minúsculas

**Ejemplo:**
```python
limpiar_nombre_carpeta("San Pedro del Paraná")
# Resultado: "san_pedro_del_parana"

limpiar_nombre_carpeta("Colonia N° 24")
# Resultado: "colonia_n_24"
```

---

### 2. `path_relevamiento_upload(instance, filename)`
**Propósito:** Genera la ruta para archivos generales (archivos comprimidos, documentos).

**Uso en modelos:**
```python
class ArchivoSubcoordinador(models.Model):
    archivo = models.FileField(
        upload_to=path_relevamiento_upload,
        verbose_name="Archivo Comprimido"
    )
```

**Ejemplo de ruta generada:**
```
relevamiento/san_pedro/distrito_1/colonia_nueva_esperanza/2026-02-25/archivo_subcoordinador.zip
```

**Campos requeridos:**
- `instance.orden_trabajo` → Orden de Trabajo
- `instance.orden_trabajo.colonia` → Colonia
- `instance.orden_trabajo.colonia.distritos.first()` → Distrito
- `distrito.departamento` → Departamento
- `instance.orden_trabajo.fecha_creacion` → Fecha de creación

---

### 3. `path_relevamiento_fotos_upload(instance, filename)`
**Propósito:** Genera la ruta para fotos y documentos adjuntos (subcarpeta `FOTOS`).

**Uso en modelos:**
```python
class FotoRelevamiento(models.Model):
    foto = models.ImageField(
        upload_to=path_relevamiento_fotos_upload,
        verbose_name="Fotografía"
    )

class Documento(models.Model):
    archivo = models.FileField(
        upload_to=path_relevamiento_fotos_upload
    )
```

**Ejemplo de ruta generada:**
```
relevamiento/san_pedro/distrito_1/colonia_nueva_esperanza/2026-02-25/FOTOS/vivienda_frente.jpg
```

**Compatibilidad:**
- Puede obtener `orden_trabajo` directamente desde `instance.orden_trabajo`
- O desde `instance.relevamiento.orden_trabajo` (para modelos relacionados)

---

## 📋 Modelos Actualizados

### 1. **ArchivoSubcoordinador**
Archivos comprimidos subidos por subcoordinadores.
```python
class ArchivoSubcoordinador(models.Model):
    orden_trabajo = models.ForeignKey('coordinacion.OrdenTrabajo', ...)
    archivo = models.FileField(upload_to=path_relevamiento_upload)
    # Ruta: relevamiento/{depto}/{distrito}/{colonia}/{fecha_OT}/archivo.zip
```

### 2. **Relevamiento**
Campo de archivo opcional en el modelo principal.
```python
class Relevamiento(models.Model):
    archivo_subcoordinador = models.FileField(
        upload_to=path_relevamiento_upload
    )
    # Ruta: relevamiento/{depto}/{distrito}/{colonia}/{fecha_OT}/archivo.rar
```

### 3. **Documento**
Documentos adjuntos (recibos, constancias, planos, etc.).
```python
class Documento(models.Model):
    relevamiento = models.ForeignKey(Relevamiento, ...)
    archivo = models.FileField(upload_to=path_relevamiento_fotos_upload)
    # Ruta: relevamiento/{depto}/{distrito}/{colonia}/{fecha_OT}/FOTOS/recibo.pdf
```

### 4. **FotoRelevamiento** (NUEVO)
Fotos tomadas durante el relevamiento de campo.
```python
class FotoRelevamiento(models.Model):
    relevamiento = models.ForeignKey(Relevamiento, ...)
    foto = models.ImageField(upload_to=path_relevamiento_fotos_upload)
    tipo_foto = models.CharField(...)  # vivienda_frente, lote_general, etc.
    # Ruta: relevamiento/{depto}/{distrito}/{colonia}/{fecha_OT}/FOTOS/foto.jpg
```

---

## 💡 Ejemplos de Uso

### Subir un archivo desde una vista
```python
from relevamiento.models import ArchivoSubcoordinador

def subir_archivo(request, orden_trabajo_id):
    orden = OrdenTrabajo.objects.get(id=orden_trabajo_id)
    archivo = request.FILES.get('archivo')
    
    # El archivo se organiza automáticamente
    archivo_obj = ArchivoSubcoordinador.objects.create(
        orden_trabajo=orden,
        archivo=archivo,
        nombre_archivo=archivo.name,
        subido_por=request.user
    )
    
    # Ruta final: media/relevamiento/san_pedro/distrito_1/colonia_nueva/2026-02-25/archivo.zip
    print(archivo_obj.archivo.path)
```

### Subir una foto desde el formulario
```python
from relevamiento.models import FotoRelevamiento

def subir_foto(request, relevamiento_id):
    relevamiento = Relevamiento.objects.get(id=relevamiento_id)
    foto = request.FILES.get('foto')
    
    foto_obj = FotoRelevamiento.objects.create(
        relevamiento=relevamiento,
        foto=foto,
        tipo_foto='vivienda_frente',
        encuestador=request.user,
        descripcion='Frente de la vivienda principal'
    )
    
    # Ruta: media/relevamiento/san_pedro/distrito_1/colonia_nueva/2026-02-25/FOTOS/foto.jpg
    print(foto_obj.foto.url)
```

### Acceder a archivos en templates
```django
{% for foto in relevamiento.fotos.all %}
    <img src="{{ foto.foto.url }}" alt="{{ foto.get_tipo_foto_display }}">
    <p>{{ foto.descripcion }}</p>
{% endfor %}
```

---

## 🔍 Manejo de Errores

Si hay algún problema al obtener los datos geográficos o la fecha, el sistema usa rutas por defecto:

**Archivos generales (fallback):**
```
media/relevamiento/otros/archivo.zip
```

**Fotos (fallback):**
```
media/relevamiento/otros/FOTOS/foto.jpg
```

Los errores se registran en la consola para facilitar el debugging.

---

## 📊 Ventajas de esta Estructura

1. **Organización Automática**: No se necesita crear carpetas manualmente
2. **Escalabilidad**: Fácil de navegar incluso con miles de archivos
3. **Trazabilidad**: Cada archivo está vinculado a su ubicación geográfica
4. **Consistencia**: Los nombres de carpetas se limpian automáticamente
5. **Separación**: Fotos en subcarpeta `FOTOS` para mejor organización

---

## 🛠️ Migraciones Aplicadas

```bash
# Crear migración
python manage.py makemigrations relevamiento

# Aplicar migración
python manage.py migrate relevamiento
```

**Migración creada:** `0006_alter_archivosubcoordinador_archivo_and_more.py`
- Actualiza `ArchivoSubcoordinador.archivo` → `path_relevamiento_upload`
- Actualiza `Documento.archivo` → `path_relevamiento_fotos_upload`
- Actualiza `Relevamiento.archivo_subcoordinador` → `path_relevamiento_upload`
- Crea modelo `FotoRelevamiento`

---

## 📝 Notas Importantes

1. **Archivos Existentes**: Los archivos subidos antes de esta actualización permanecen en su ubicación original. Solo los nuevos archivos usan la nueva estructura.

2. **Formato de Fecha**: El formato de la carpeta de fecha es `YYYY-MM-DD` (ej: `2026-02-25`).

3. **Nombres Limpios**: Todos los nombres de carpetas se convierten a minúsculas y sin caracteres especiales para compatibilidad.

4. **ImageField vs FileField**: 
   - `ImageField` valida que el archivo sea una imagen
   - `FileField` acepta cualquier tipo de archivo

5. **Performance**: La estructura de carpetas no afecta el rendimiento de Django. El acceso a archivos sigue siendo igual de rápido.

---

## 🔄 Migración de Archivos Antiguos (Opcional)

Si deseas mover archivos existentes a la nueva estructura, puedes crear un comando de management:

```python
# relevamiento/management/commands/migrar_archivos.py
from django.core.management.base import BaseCommand
from relevamiento.models import ArchivoSubcoordinador

class Command(BaseCommand):
    def handle(self, *args, **options):
        for archivo in ArchivoSubcoordinador.objects.all():
            archivo.save()  # Esto forzará la regeneración de la ruta
            self.stdout.write(f"Migrado: {archivo.nombre_archivo}")
```

Ejecutar:
```bash
python manage.py migrar_archivos
```

---

## 📞 Soporte

Para dudas o problemas con la estructura de archivos, contactar al equipo de desarrollo.

Última actualización: Febrero 2026
