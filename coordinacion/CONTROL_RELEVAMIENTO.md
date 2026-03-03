# Módulo de Gestión de Control de Relevamiento

## Descripción General

El módulo **Gestión de Control de Relevamiento** permite a los coordinadores identificar y gestionar "mermas" o registros problemáticos en colonias con órdenes de trabajo completadas.

## Características Implementadas

### 1. Vista Principal - Panel de Colonias

**Ubicación**: `/coordinacion/control-relevamiento/`

**Funcionalidad**:
- Lista todas las colonias que tienen órdenes de trabajo en estado **COMPLETADO**
- Muestra información geográfica (departamento, distrito)
- Indica cuántas órdenes completadas tiene cada colonia
- Muestra la fecha de la última orden completada
- Botón **"Obtener Datos"** para cargar mermas de cada colonia

**Columnas de la tabla**:
- Número consecutivo
- Nombre de la colonia
- Distrito
- Departamento
- Cantidad de órdenes completadas
- Fecha de última orden completada
- Botón de acción

### 2. Sistema de Carga AJAX

**Endpoint**: `/coordinacion/control-relevamiento/mermas/<colonia_id>/`

**Método**: GET con petición AJAX

**Funcionalidad**:
- Carga asíncrona sin recargar la página
- Spinner de carga visual mientras procesa
- Filtrado estricto de registros problemáticos:
  - **AUSENTE**: `condicion_vivienda == "ausente"`
  - **RECHAZADO**: `estado_entrevista == "rechazo"`
  - **EN CONFLICTO**: `estado_entrevista == "en_conflicto"`

**Respuesta JSON**:
```json
{
  "success": true,
  "colonia": {
    "nombre": "Nombre Colonia",
    "id": 123
  },
  "kpis": {
    "lotes_digitalizados": 150,
    "meta_relevamiento": 120,
    "total_relevamientos": 115,
    "relevamientos_exitosos": 100,
    "total_mermas": 15,
    "porcentaje_exito": 87.0
  },
  "mermas": [
    {
      "id": 1,
      "manzana": "A",
      "lote": "123",
      "ocupante": "Juan Pérez",
      "estado": "Ausente",
      "encuestador": "María López",
      "fecha": "15/02/2026"
    }
  ]
}
```

### 3. Dashboard de Detalle (Carga Dinámica)

**Sección de KPIs** (4 tarjetas):
1. **Lotes Digitalizados**: Total de lotes del Precat más reciente
2. **Meta de Relevamiento**: Suma de metas de todas las órdenes
3. **Relevamientos Exitosos**: Total menos mermas
4. **Tasa de Éxito**: Porcentaje de relevamientos exitosos
   - Verde (≥80%): Excelente
   - Amarillo (60-79%): Aceptable
   - Rojo (<60%): Crítico

**Tabla de Mermas**:
- Número consecutivo
- Manzana
- Lote (SIRT o INDERT)
- Nombre del encuestado
- Estado (badge con color):
  - **Ausente**: Badge amarillo
  - **Rechazado**: Badge rojo
  - **En Conflicto**: Badge gris
- Encuestador responsable
- Fecha del registro

**Estado Vacío**:
- Si no hay mermas, muestra mensaje de éxito

## Acceso al Módulo

### Desde el Dashboard de Coordinación

En el dashboard principal de coordinación (`/coordinacion/dashboard/`), se ha agregado un botón **"Control de Relevamiento"** en la esquina superior derecha.

### Permisos Requeridos

- Login requerido: `@login_required`
- Rol de coordinación: `@coordinacion_required`

## Arquitectura Técnica

### Archivos Modificados/Creados

1. **Backend**:
   - `coordinacion/views.py`: 
     - `control_relevamiento_panel()` - Vista principal
     - `control_relevamiento_obtener_mermas()` - Endpoint AJAX

2. **Frontend**:
   - `templates/coordinacion/control_relevamiento/panel.html` - Template principal

3. **Routing**:
   - `coordinacion/urls.py` - Dos nuevas rutas

4. **Dashboard**:
   - `templates/coordinacion/coordinacion_dashboard.html` - Botón de acceso

### Tecnologías Utilizadas

- **Backend**: Django 4.x, Python
- **Frontend**: Bootstrap 5, JavaScript Vanilla (sin frameworks)
- **AJAX**: Fetch API nativa
- **Animaciones**: CSS3 keyframes

### Consultas Optimizadas

```python
# Query optimizada con select_related y prefetch_related
ordenes_completadas = OrdenTrabajo.objects.filter(
    estado='completada'
).select_related(
    'solicitud',
    'solicitud__colonia'
).prefetch_related(
    'solicitud__colonia__distritos__departamento'
)

# Filtro de mermas con Q objects
mermas = Relevamiento.objects.filter(
    colonia=colonia,
    orden_trabajo_id__in=orden_ids
).filter(
    Q(condicion_vivienda='ausente') |
    Q(estado_entrevista='rechazo') |
    Q(estado_entrevista='en_conflicto')
)
```

## Flujo de Usuario

1. **Coordinador ingresa al dashboard** → Ve botón "Control de Relevamiento"
2. **Click en el botón** → Carga panel con lista de colonias completadas
3. **Click en "Obtener Datos"** de una colonia → Spinner aparece
4. **Sistema carga datos via AJAX** → Petición al servidor
5. **Servidor procesa y filtra mermas** → Calcula KPIs
6. **JavaScript renderiza dashboard** → Muestra KPIs y tabla
7. **Scroll automático** → Animación suave hacia la sección de detalle
8. **Usuario revisa mermas** → Identifica problemas por manzana/lote
9. **Click en "Cerrar"** → Oculta detalle y vuelve arriba

## Casos de Uso

### Caso 1: Identificar zonas problemáticas
Un coordinador necesita saber qué lotes tienen problemas después de completar un relevamiento. Usa el módulo para ver las mermas y planificar un segundo relevamiento.

### Caso 2: Evaluar productividad
El coordinador compara los lotes digitalizados vs. la meta y los relevamientos exitosos para evaluar el desempeño del equipo.

### Caso 3: Auditoría post-relevamiento
Después de marcar una orden como completada, se revisa el módulo para validar que no haya quedado ninguna merma sin atender.

## Mejoras Futuras (Opcionales)

- [ ] Exportar mermas a Excel/CSV
- [ ] Filtros adicionales (por fecha, encuestador, tipo de merma)
- [ ] Gráficos de tendencias (Chart.js)
- [ ] Botón para reasignar mermas específicas
- [ ] Notificaciones automáticas cuando hay mermas críticas
- [ ] Historial de mermas resueltas

## Notas Técnicas

### Estados de Entrevista Válidos
Según `relevamiento/models.py`:
```python
ESTADO_ENTREVISTA = [
    ("completa", "Completa"),
    ("rechazo", "Rechazo"),
    ("parcial", "Parcial"),
    ("en_conflicto", "En Conflicto"),
]
```

### Condiciones de Vivienda Válidas
```python
COND_VIVIENDA_CHOICES = [
    ("presente", "Presente"),
    ("ausente", "Ausente"),
    ("sin_vivienda", "Sin vivienda"),
    ("servicio", "Servicio"),
]
```

### Rendimiento
- Las consultas están optimizadas con `select_related` y `prefetch_related`
- El filtrado de mermas usa índices de base de datos
- La carga AJAX evita recargar toda la página
- Los KPIs se calculan en el servidor (no en el cliente)

## Soporte

Para reportar bugs o solicitar mejoras, contactar al equipo de desarrollo.
