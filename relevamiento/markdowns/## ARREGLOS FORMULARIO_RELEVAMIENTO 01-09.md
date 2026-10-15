## ARREGLOS FORMULARIO_RELEVAMIENTO.HTML
- HACER EL FORMULARIO MÁS DINAMICO
ESTA PRIMERA PARTE: 
MANEJA LAS SECCIONES DE ocupante (default), conflicto, servicio, fraccionamiento.

<!-- ============================================================ -->
<!-- SELECTOR DE MODO DE RELEVAMIENTO -->
<!-- ============================================================ -->
    <div class="card mb-4">
      <div class="card-body py-3">
        <div class="btn-group w-100" role="group" aria-label="Modo de registro">
          <button type="button" class="btn btn-outline-primary {% if not pretendiente_formset %}active{% endif %}" data-mode="ocupante" onclick="switchMode('ocupante')">
            <i class="fas fa-user me-1"></i> Ocupante
          </button>
          <button type="button" class="btn btn-outline-primary {% if pretendiente_formset %}active{% endif %}" data-mode="conflicto" onclick="switchMode('conflicto')">
            <i class="fas fa-users me-1"></i> Conflicto
          </button>
          <button type="button" class="btn btn-outline-primary" data-mode="servicio" onclick="switchMode('servicio')">
            <i class="fas fa-building me-1"></i> Servicio
          </button>
          <button type="button" class="btn btn-outline-primary" data-mode="fraccionamiento" onclick="switchMode('fraccionamiento')">
            <i class="fas fa-cut me-1"></i> Fraccionamiento
          </button>
        </div>
      </div>
    </div>
    <input type="hidden" name="tipo_relevamiento" id="tipo_relevamiento" value="{% if pretendiente_formset %}conflicto{% else %}ocupante{% endif %}">

Ocupante maneja: 
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

ok, centremonos en esta primera pesteña default de ocupante.
para conflicto, servicio y fraccionamiento que me muestre en cada uno un mensajesito estoy en la pestaña "conflicto" o "servicio" o "fraccionamiento" para cada caso.