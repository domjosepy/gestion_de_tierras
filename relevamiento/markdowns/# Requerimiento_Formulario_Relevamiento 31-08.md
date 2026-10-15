# Especificación de Requerimientos Funcionales - Formulario de Relevamiento (Censo de Campo)

---

## 1. Visión General del Sistema
El **Formulario de Relevamiento** es una herramienta destinada a la captura de datos en censo de campo, diseñada para ejecutarse de manera responsiva en dispositivos móviles, tablets y ordenadores portátiles (laptops). Permite registrar datos geográficos, catastrales, sociodemográficos, productivos y habitacionales de predios/lotes.

---

## 2. Definición del Flujo General y Navegación

### 2.1. Arquitectura de Interfaz Recomendada
* **Modalidad Recomendada:** **Wizard Paso a Paso (Multi-step con Secciones Colapsables)**.
  * **Justificación:** Dada la complejidad de los flujos condicionales (modales, sub-tablas de población, múltiples pretendientes y fraccionamientos), una estructura por pasos previene la saturación visual en dispositivos móviles/tablets y garantiza que los datos requeridos se completen de manera ordenada.
  * **Indicador de Progreso:** Barra superior con estados de la encuesta (Geográfico $\rightarrow$ Tipo de Registro $\rightarrow$ Ocupación / Conflicto / Servicio $\rightarrow$ Resumen).

### 2.2. Flexibilidad de Navegación
* El encuestador **puede cambiar el modo o tipo de registro en cualquier momento** de la carga si considera necesario.

---

## 3. Estructura Completa de Módulos y Secciones

### SECCIÓN A — Datos Geográficos (Común a Todos)
Campos obligatorios al inicio de cada nueva encuesta:
- Informacion se toma de la orden de trabajo.
* **Departamento** (muestra por defecto)
* **Distrito** (muestra por defecto)
* **Colonia** (muestra por defecto)

---

### SECCIÓN B — Identificación del Lote y Selección de Flujo

#### Datos Censo / Catastrales Básicos:
* **Manzana**
* **Lote** (Lote inder = lote sirt: toma la informacion de lote indert y guarda)
* **Superficie**
* **Dimensión**

#### Tipo de Registro (Define el flujo a seguir):
1. **[I] Registro Ocupante** (Opción por defecto)
2. **[II] Registro Conflicto**
3. **[III] Registro Servicio**
4. **[IV] Registro Fraccionamiento**

---

## 4. Detalle por Tipo de Registro

```
                               ┌─────────────────────────┐
                               │  NUEVA ENCUESTA (A/B)   │
                               └────────────┬────────────┘
                                            │
           ┌────────────────────────────────┼────────────────────────────────┬────────────────────────┐
           ▼                                ▼                                ▼                        ▼
┌────────────────────┐            ┌────────────────────┐           ┌───────────────────┐    ┌────────────────────┐
│ [I] REGISTRO       │            │ [II] REGISTRO      │           │ [III] REGISTRO    │    │ [IV] REGISTRO      │
│     OCUPANTE       │            │      CONFLICTO     │           │       SERVICIO    │    │    FRACCIONAMIENTO │
└──────────┬─────────┘            └─────────┬──────────┘           └─────────┬─────────┘    └──────────┬─────────┘
           │                                │                                │                         │
           ├─ Datos Ocupante & Cónyuge      ├─ N Pretendientes (1..N)        └─ Inst / RUC / Desc      └─ Subdivisión Automática
           ├─ Datos Productivos/Ganaderos   ├─ Datos Productivos p/pretendiente                        (1 -> 1A, 1B, ...)
           ├─ Condición Vivienda            └─ Condición Vivienda p/pretendiente                       └─ N Ocupantes por Sub-lote
           └─ Población & Solo Vivienda
```

---

### MODO 1: [I] REGISTRO OCUPANTE

#### 1. Datos del Ocupante Principal
* **Nombre Ocupante**
* **Cédula de Identidad (CI) Ocupante**
* **Sexo Ocupante**
* **Estado Civil Ocupante**
* **Botón Modal: `{Datos del Cónyuge}`**
  * *Nombre Cónyuge*
  * *CI Cónyuge*
  * *Estado Civil Cónyuge*
  * *Sexo Cónyuge:* Por defecto se asigna automáticamente el sexo opuesto al del ocupante (editable si se requiere).

#### 2. Datos Productivos, Ganaderos e Infraestructura
* Aplican al lote ocupado (Uso del lote, mejoras, producción agropecuaria, ganadería).

#### 3. Condición de la Vivienda y Lógica Condicional

##### Regla Automática de Residencia:
* Si `Condición de Vivienda == 1. Presente` $\rightarrow$ Se marca automáticamente `vive_en_lote = True`.
* Si el encuestador cambia manualmente `vive_en_lote = False` O si `Condición de Vivienda == 4. Sin vivienda`:
  * Se habilita el botón y modal **`{Agregar Información de Residencia}`**:
    * *Manzana de residencia*
    * *Lote de residencia*
    * *Ocupante del lote donde reside*
    * *Parentesco con dicho ocupante*

##### Evaluador de Estados de Vivienda:

| Condición Seleccionada | Acción / Modal Desplegado | Captura de Fotos |
| :--- | :--- | :--- |
| **1. Presente** | Modal de **Características de la vivienda** (Checkboxes) + **Equipamiento de vivienda** (Checkboxes). Al guardar, habilita la sub-tabla de **Registro de Población**. | Se habilita botón **Capturar Foto de Vivienda** (Obligatorio). |
| **2. Ausente** | Modal de **Características de la vivienda** (Checkboxes) + **Equipamiento de vivienda** (Checkboxes). | Opcional / Según requerimiento. |
| **3. En Construcción** | Modal de **Características de la vivienda** (Checkboxes). | Opcional / Según requerimiento. |
| **4. Sin Vivienda** | Despliega directamente el Modal de **Información de Residencia del Ocupante**. | N/A |

---

#### 4. Tabla Dinámica: Registro de Población
Disponible tras confirmar/guardar la vivienda de ocupante presente. Registra la cantidad de personas que residen en el lote.

| Orden | Nombres | Cédula | Edad | Relación de Parentesco | Grado |
| :---: | :--- | :--- | :---: | :--- | :---: |
| 1 | *Ej: FULANO* | *123456* | 20 | **Jefe de hogar** (Opción por defecto para Titular) | - |
| 2 | *Ej: MENCANO* | *654321* | 18 | Cónyuge, Hijo/a, Hermano/a, Tío/a, Abuelo/a, Sobrino/a, Ahijado/a, Cuñado/a, etc. | Sexto |

---

#### 5. Módulo Adicional: "Solo Vivienda" (Viviendas Adicionales)
Permite registrar una o múltiples viviendas adicionales construidas dentro del mismo lote (sean de parientes o no parientes).
* **Cantidad de Viviendas Adicionales:** Múltiple ($1..N$).
* **Población Propia:** Cada unidad de "Solo Vivienda" posee su propia sub-tabla independiente de registro de población.
* **Captura Fotográfica:** Al completar las características de "Solo Vivienda", se muestra/habilita el botón **Agregar Foto (Solo Vivienda)** (Obligatoria).

---

### MODO 2: [II] REGISTRO CONFLICTO

Se aplica cuando existen dos o más partes que reclaman el mismo lote.

* **Lista de Pretendientes:** Permite agregar $N$ pretendientes mediante el botón `{+ Agregar otro pretendiente}` (Pretendiente 1, Pretendiente 2, etc.).
* **Campos por Pretendiente:**
  * Nombre, CI, Sexo, Estado Civil.
  * Datos del Cónyuge (Modal).
* **Manejo Independiente por Pretendiente:**
  * **Datos Productivos y Ganaderos:** Cada pretendiente declara sus propios datos productivos/ganaderos de manera independiente.
  * **Condición de Vivienda:** Aplica la misma lógica condicional (Presente, Ausente, En Construcción, Sin Vivienda), modales de características/equipamiento, captura de fotos y tabla de población de forma individual para cada pretendiente.

---

### MODO 3: [III] REGISTRO SERVICIO

Para lotes destinados a equipamiento comunitario o instituciones públicas/privadas.

#### Campos de Registro Único:
* **Institución** (Ej: Ministerio de Salud)
* **Número de RUC** (Ej: 8000000044-2)
* **Descripción** (Ej: Puesto de Salud)

*(No requiere agregar datos sociodemográficos, de población ni productivos adicionales).*

---

### MODO 4: [IV] REGISTRO FRACCIONAMIENTO

Se utiliza cuando un lote original está en proceso de subdivisión en múltiples sub-lotes.

#### Lógica de Nomenclatura Automática:
* Si el lote original es `1`, la primera subdivisión genera el sub-lote `1A`.
* Presionar el botón **`[Realizar Fraccionamiento]`** genera secuencialmente los sub-lotes: `1B`, `1C`, `1D`, etc.

#### Estructura de Captura por Sub-lote:
* Se registran múltiples sub-lotes, cada uno con sus respectivos datos.
* **Contenido por Sub-lote:** Cada sub-lote contiene exactamente la misma información que un **[I] Registro Ocupante** completo (Ocupante, Cónyuge, Condición de Vivienda, Fotos, Población, Datos Productivos, Ganaderos y "Solo Vivienda").

---

## 5. Reglas de Negocio Específicas

### 5.1. Reglas Fotográficas
* **Obligatoriedad:** Las fotografías de vivienda (tanto principal como "Solo Vivienda") son **obligatorias**.
* **Cantidad:** Sin límite prefijado (las fotos que se consideren necesarias).
* **Origen de Captura:**
  * **Cámara en tiempo real:** Habilitada por defecto para la toma directa en campo.
  * **Galería del dispositivo:** Deshabilitada por defecto. Solo se permite subir desde la galería si un **Coordinador** habilita explícitamente el permiso de edición.

### 5.2. Reglas Sociodemográficas
* **Sexo del Cónyuge:** Por defecto es el valor opuesto al sexo seleccionado para el Ocupante/Pretendiente, pero permanece **editable** para el encuestador.
* **Límite de Pretendientes:** Sin restricción (1 a $N$).

---

## 6. Resumen de Matriz de Funcionalidades por Modo

| Funcionalidad / Módulo | [I] Ocupante | [II] Conflicto | [III] Servicio | [IV] Fraccionamiento |
| :--- | :---: | :---: | :---: | :---: |
| **Datos Geográficos** | Sí | Sí | Sí | Sí |
| **Datos de Cónyuge** | Sí | Sí (Por pretendiente) | No | Sí (Por sub-lote) |
| **Datos Productivos y Ganaderos** | Sí | Sí (Por pretendiente) | No | Sí (Por sub-lote) |
| **Condición de Vivienda / Fotos** | Sí | Sí (Por pretendiente) | No | Sí (Por sub-lote) |
| **Tabla de Población** | Sí | Sí (Por pretendiente) | No | Sí (Por sub-lote) |
| **Módulo "Solo Vivienda"** | Sí | Sí (Por pretendiente) | No | Sí (Por sub-lote) |
| **Lógica de Subdivisión (1A, 1B...)**| No | No | No | **Sí (Automática)** |


# Resumen de la Estructuración RealizadaHe consolidado la información del formulario junto con todas tus respuestas aclaratorias en una especificación clara, profesional y técnica:

- Recomendación de Interfaz (Wizard Paso a Paso): Dada la complejidad de los flujos condicionales (población, fotos, modales, pretendientes) y su uso en dispositivos móviles/tablets, se definió la navegación en formato Wizard manteniendo la capacidad de cambiar de modo en cualquier momento.
- Flujos de Registro Detallados:
* [I] Registro Ocupante: Flujo principal con cónyuge (sexo opuesto por defecto), condicionales de vivienda, modales de características, sub-tabla dinámica de población, regla automática para vive_en_lote y soporte para múltiples registros de "Solo vivienda" con población y fotos independientes.
* [II] Registro Conflicto: Estructurado para $N$ pretendientes, donde cada uno maneja de forma independiente sus propios datos productivos, ganaderos, vivienda, fotos y población.
* [III] Registro Servicio: Flujo simplificado únicamente para instituciones (Nombre, RUC, Descripción).
* [IV] Registro Fraccionamiento: Lógica de nomenclatura automática secuencial (1 $\rightarrow$ 1A, 1B, 1C...) donde cada sub-lote hereda la estructura completa del registro de ocupante.Reglas de Negocio Incorporadas:Fotos: Obligatorias (captura con cámara directa en campo; carga desde galería bloqueada excepto bajo habilitación expresa de un coordinador).Flexibilidad de Navegación: Permite ajustar el tipo de registro a mitad de carga.

aplicar los campos necesarios de /relevamiento/models.py, relevamiento/forms.py relevamiento/views.py para su correcto funcionamiento