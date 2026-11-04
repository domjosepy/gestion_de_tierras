# ✅ RESUMEN DE IMPLEMENTACIÓN 
## Estructura de Carpetas Automática para Archivos de Relevamiento

---

## 📦 ARCHIVOS MODIFICADOS/CREADOS

### 1. **relevamiento/models.py** ✅
- ✅ Agregadas funciones de utilidad:
  - `limpiar_nombre_carpeta(nombre)` → Limpia nombres para filesystem
  - `path_relevamiento_upload(instance, filename)` → Ruta para archivos generales
  - `path_relevamiento_fotos_upload(instance, filename)` → Ruta para fotos

- ✅ Modelos actualizados con funciones personalizadas:
  - `ArchivoSubcoordinador.archivo` → usa `path_relevamiento_upload`
  - `Relevamiento.archivo_subcoordinador` → usa `path_relevamiento_upload`
  - `Documento.archivo` → usa `path_relevamiento_fotos_upload`

- ✅ Nuevo modelo creado:
  - `FotoRelevamiento` → Modelo completo para fotos de encuestadores
    - Campo `foto` (ImageField) con `path_relevamiento_fotos_upload`
    - Tipos de foto: vivienda_frente, vivienda_lateral, lote_general, etc.
    - Coordenadas GPS (latitud/longitud)
    - Descripción y encuestador

### 2. **relevamiento/admin.py** ✅
- ✅ Registrados en admin:
  - `RelevamientoAdmin` → Con filtros y búsqueda
  - `FotoRelevamientoAdmin` → Con vista previa de imagen
  - `ArchivoSubcoordinadorAdmin` → Con filtros por fecha
  - `DocumentoAdmin` → Con búsqueda por tipo

### 3. **relevamiento/UPLOAD_ESTRUCTURA.md** ✅
- ✅ Documentación completa incluyendo:
  - Descripción de la estructura de carpetas
  - Ejemplos de rutas generadas
  - Documentación de funciones
  - Ejemplos de uso en vistas y templates
  - Manejo de errores

### 4. **relevamiento/test_upload_paths.py** ✅
- ✅ Tests unitarios para `limpiar_nombre_carpeta`
  - Test de eliminación de espacios
  - Test de caracteres especiales
  - Test de conversión a minúsculas
  - Test de valores None/vacíos

### 5. **Migraciones** ✅
- ✅ Migración `0006_alter_archivosubcoordinador_archivo_and_more.py` creada y aplicada
  - Actualiza campos FileField con nuevas funciones upload_to
  - Crea tabla `relevamiento_fotorelevamiento`

---

## 🗂️ ESTRUCTURA GENERADA

### Archivos Generales (Subcoordinadores)
```
media/
└── relevamiento/
    └── san_pedro/                    ← Departamento (limpio)
        └── distrito_central/          ← Distrito (limpio)
            └── colonia_nueva_esperanza/  ← Colonia (limpio)
                └── 2026-02-25/            ← Fecha OT (YYYY-MM-DD)
                    ├── archivo1.zip
                    ├── archivo2.rar
                    └── datos.7z
```

### Fotos de Encuestadores
```
media/
└── relevamiento/
    └── san_pedro/
        └── distrito_central/
            └── colonia_nueva_esperanza/
                └── 2026-02-25/
                    └── FOTOS/                ← Subcarpeta FOTOS
                        ├── vivienda_frente.jpg
                        ├── lote_general.jpg
                        ├── documento_titulo.pdf
                        └── familia.jpg
```

---

## 🔧 FUNCIONES IMPLEMENTADAS

### 1. `limpiar_nombre_carpeta(nombre)`
```python
Input:  "San Pedro del Paraná"
Output: "san_pedro_del_parana"

Input:  "Colonia N° 24"
Output: "colonia_n_24"

Input:  "DISTRITO NORTE"
Output: "distrito_norte"
```

**Procesamiento:**
- Elimina espacios → `_`
- Elimina caracteres especiales
- Convierte a minúsculas
- Mantiene números, `-`, `_`

---

### 2. `path_relevamiento_upload(instance, filename)`
**Para:** Archivos comprimidos y documentos generales

**Entrada:**
```python
instance = ArchivoSubcoordinador
filename = "relevamiento_colonia_24.zip"
```

**Salida:**
```
"relevamiento/san_pedro/distrito_1/colonia_24/2026-02-25/relevamiento_colonia_24.zip"
```

**Requiere:**
- `instance.orden_trabajo.solicitud.colonia`
- `instance.orden_trabajo.fecha_creacion`

---

### 3. `path_relevamiento_fotos_upload(instance, filename)`
**Para:** Fotos de encuestadores y documentos adjuntos

**Entrada:**
```python
instance = FotoRelevamiento
filename = "foto_vivienda.jpg"
```

**Salida:**
```
"relevamiento/san_pedro/distrito_1/colonia_24/2026-02-25/FOTOS/foto_vivienda.jpg"
```

**Soporta:**
- `instance.orden_trabajo` (directo)
- `instance.relevamiento.orden_trabajo` (indirecto)

---

## 💻 EJEMPLOS DE USO

### Crear archivo desde vista (Subcoordinador)
```python
from relevamiento.models import ArchivoSubcoordinador

def subir_archivo(request, orden_trabajo_id):
    orden = OrdenTrabajo.objects.get(id=orden_trabajo_id)
    archivo = request.FILES.get('archivo')
    
    # Crear registro - la ruta se genera automáticamente
    archivo_obj = ArchivoSubcoordinador.objects.create(
        orden_trabajo=orden,
        archivo=archivo,
        nombre_archivo=archivo.name,
        subido_por=request.user
    )
    
    # Resultado: media/relevamiento/caaguazu/coronel_oviedo/colonia_primavera/2026-03-15/archivo.zip
    print(f"Archivo guardado en: {archivo_obj.archivo.path}")
```

### Crear foto desde formulario (Encuestador)
```python
from relevamiento.models import FotoRelevamiento

def subir_foto(request, relevamiento_id):
    relevamiento = Relevamiento.objects.get(id=relevamiento_id)
    foto = request.FILES.get('foto')
    
    foto_obj = FotoRelevamiento.objects.create(
        relevamiento=relevamiento,
        foto=foto,
        tipo_foto='vivienda_frente',
        descripcion='Fachada principal de la vivienda',
        encuestador=request.user,
        latitud=-25.2637,
        longitud=-57.5759
    )
    
    # Resultado: media/relevamiento/.../FOTOS/foto.jpg
    return foto_obj.foto.url  # Para usar en template
```

### Mostrar fotos en template
```django
{% for foto in relevamiento.fotos.all %}
    <div class="foto-item">
        <img src="{{ foto.foto.url }}" alt="{{ foto.get_tipo_foto_display }}">
        <p><strong>{{ foto.get_tipo_foto_display }}</strong></p>
        <p>{{ foto.descripcion }}</p>
        <small>Por: {{ foto.encuestador.username }} - {{ foto.fecha_captura|date:"d/m/Y H:i" }}</small>
    </div>
{% endfor %}
```

### Listar archivos de subcoordinador
```django
{% for archivo in orden.archivos_subcoordinador.all %}
    <div class="archivo-item">
        <a href="{{ archivo.archivo.url }}" download>
            <i class="fas fa-file-archive"></i>
            {{ archivo.nombre_archivo }}
        </a>
        <small>{{ archivo.fecha_subida|date:"d/m/Y H:i" }}</small>
    </div>
{% endfor %}
```

---

## 🛡️ MANEJO DE ERRORES

**Si hay problemas al obtener datos geográficos:**
```
Ruta por defecto (archivos): media/relevamiento/otros/archivo.zip
Ruta por defecto (fotos):    media/relevamiento/otros/FOTOS/foto.jpg
```

**Los errores se registran en consola:**
```python
print(f"Error al generar ruta de subida: {e}")
```

---

## 📊 MODELO FOTORELEVAMIENTO (Nuevo)

```python
class FotoRelevamiento(models.Model):
    relevamiento = ForeignKey(Relevamiento)
    foto = ImageField(upload_to=path_relevamiento_fotos_upload)
    tipo_foto = CharField(choices=[
        ('vivienda_frente', 'Vivienda - Frente'),
        ('vivienda_lateral', 'Vivienda - Lateral'),
        ('vivienda_fondo', 'Vivienda - Fondo'),
        ('lote_general', 'Vista General del Lote'),
        ('mejoras', 'Mejoras/Construcciones'),
        ('cultivos', 'Cultivos'),
        ('documento', 'Documento/Título'),
        ('familia', 'Familia'),
        ('otro', 'Otro'),
    ])
    descripcion = CharField(max_length=255)
    encuestador = ForeignKey(User)
    fecha_captura = DateTimeField(auto_now_add=True)
    latitud = DecimalField(max_digits=10, decimal_places=8)
    longitud = DecimalField(max_digits=11, decimal_places=8)
```

**Acceso desde relevamiento:**
```python
relevamiento = Relevamiento.objects.get(id=1)
fotos = relevamiento.fotos.all()
fotos_vivienda = relevamiento.fotos.filter(tipo_foto__startswith='vivienda')
```

---

## 🎯 VENTAJAS

1. ✅ **Organización Automática** - No requiere crear carpetas manualmente
2. ✅ **Escalable** - Funciona con miles de archivos
3. ✅ **Trazable** - Cada archivo vinculado a ubicación geográfica
4. ✅ **Consistente** - Nombres limpios y estandarizados
5. ✅ **Separado** - Fotos en subcarpeta `FOTOS/`
6. ✅ **Robusto** - Manejo de errores con rutas por defecto
7. ✅ **Documentado** - Código autodocumentado con docstrings

---

## 🚀 PRÓXIMOS PASOS (Opcionales)

### 1. Agregar formulario de subida de fotos en template
```django
<form method="post" enctype="multipart/form-data" action="{% url 'relevamiento:subir_foto' relevamiento.id %}">
    {% csrf_token %}
    <input type="file" name="foto" accept="image/*">
    <select name="tipo_foto">
        <option value="vivienda_frente">Vivienda - Frente</option>
        <option value="lote_general">Vista General</option>
        <!-- ... más opciones -->
    </select>
    <input type="text" name="descripcion" placeholder="Descripción">
    <button type="submit">Subir Foto</button>
</form>
```

### 2. Crear vista para subir fotos
```python
@login_required
def subir_foto(request, relevamiento_id):
    if request.method == 'POST':
        relevamiento = get_object_or_404(Relevamiento, id=relevamiento_id)
        foto = request.FILES.get('foto')
        tipo_foto = request.POST.get('tipo_foto')
        descripcion = request.POST.get('descripcion', '')
        
        FotoRelevamiento.objects.create(
            relevamiento=relevamiento,
            foto=foto,
            tipo_foto=tipo_foto,
            descripcion=descripcion,
            encuestador=request.user
        )
        
        messages.success(request, 'Foto subida correctamente')
        return redirect('relevamiento:detalle', relevamiento_id)
```

### 3. Agregar vista de galería de fotos
```django
<div class="gallery">
    {% for foto in relevamiento.fotos.all %}
        <div class="gallery-item">
            <a href="{{ foto.foto.url }}" data-lightbox="galeria">
                <img src="{{ foto.foto.url }}" alt="{{ foto.descripcion }}">
            </a>
        </div>
    {% endfor %}
</div>
```

---

## ✅ ESTADO FINAL

| Componente | Estado | Detalles |
|------------|--------|----------|
| Funciones upload_to | ✅ | Implementadas y funcionales |
| Limpieza de nombres | ✅ | Regex y validaciones aplicadas |
| Modelo FotoRelevamiento | ✅ | Creado con todos los campos |
| Migraciones | ✅ | Aplicadas (0006) |
| Admin | ✅ | Registrados todos los modelos |
| Documentación | ✅ | UPLOAD_ESTRUCTURA.md completo |
| Tests | ✅ | test_upload_paths.py creado |

---

**✨ IMPLEMENTACIÓN COMPLETA Y LISTA PARA USAR ✨**

Fecha: 25 de Febrero de 2026
