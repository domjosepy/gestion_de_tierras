## ARREGLOS DINAMICOS Y DE DISEÑO 
# DE FORMULARIO DE RELEVAMIENTO

<!-- ============================================================ -->
<!-- SELECTOR DE MODO DE RELEVAMIENTO -->
<!-- ============================================================ -->
<div class="card mb-4">
    <div class="card-body py-3">
        <div class="btn-group w-100" role="group" aria-label="Modo de registro">
          <button type="button" class="btn btn-outline-primary active" data-mode="ocupante" onclick="switchMode('ocupante')">
            <i class="fas fa-user me-1"></i> Ocupante
          </button>
          <button type="button" class="btn btn-outline-primary" data-mode="conflicto" onclick="switchMode('conflicto')">
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

---------
<button type="button" class="btn btn-outline-primary active" data-mode="ocupante" onclick="switchMode('ocupante')">
            <i class="fas fa-user me-1"></i> Ocupante
</button>


Muestra: 
<!-- ============================================================ -->
<!-- SECCIÓN 2: DATOS DEL OCUPANTE/conflicto/servicio/fraccionamiento -->
<!-- ============================================================ -->
<div class="card mb-4" data-modes="ocupante fraccionamiento">
    <div class="card-header-brown-light">
        <i class="fas fa-user"></i>
        <!--si el onclick="switchMode('ocupante')" se muestra-->
        <h2 class="mb-0">3. Datos del Ocupante</h2>
    </div>
    <!-- Arreglo 1: # onclick="switchMode('ocupante')
        ### Muestra solamente los campos, quien_es_el_ocupante, 
        cedula_ocupante, sexo_ocupante, estado_civil_ocupante y 
        el boton agregar conyuge que muestra el modal -->
    <div class="card-body">
        <div class="row g-3">
        <div class="col-md-2">
            <label class="form-label fw-semibold">{{ form.quien_es_el_ocupante.label }}</label>
                {{ form.quien_es_el_ocupante }}
                {% if form.quien_es_el_ocupante.errors %}<div class="text-danger small mt-1">{{ form.quien_es_el_ocupante.errors }}</div>{% endif %}
        </div>
        <div class="col-md-4">
            <label class="form-label fw-semibold">{{ form.cedula_ocupante.label }}</label>
            {{ form.cedula_ocupante }}
            {% if form.cedula_ocupante.errors %}<div class="text-danger small mt-1">{{ form.cedula_ocupante.errors }}</div>{% endif %}
        </div>
        <div class="col-md-4">
            <label class="form-label fw-semibold">{{ form.sexo_ocupante.label }}</label>
            {{ form.sexo_ocupante }}
            {% if form.sexo_ocupante.errors %}<div class="text-danger small mt-1">{{ form.sexo_ocupante.errors }}</div>{% endif %}
        </div>
        <div class="col-md-4">
            <label class="form-label fw-semibold">{{ form.estado_civil_ocupante.label }}</label>
                {{ form.estado_civil_ocupante }}
                {% if form.estado_civil_ocupante.errors %}<div class="text-danger small mt-1">{{ form.estado_civil_ocupante.errors }}</div>{% endif %}
        </div>
        <!--Ruta de la ubicacion del modal: templates>includes>relevamiento>encuestador>modal>agregar_conyuge.html-->
        <!--arreglo 1.1: si sexo_ocupante es igual a masculino, entonces sexo_conyuge es igual a femenino y viceversa-->
        <div class="col-md-4 d-flex align-items-end">
            <button type="button" class="btn btn-outline-secondary w-100"
                        data-bs-toggle="modal" data-bs-target="#modalConyuge" data-conyuge-target="0">
            <i class="fas fa-user-friends me-1"></i> Agregar Cónyuge
            </button>
        </div>
        <!-- Arreglo 1: FIN DEL PRIMER ARREGLO ocupante -->
</div>
<!-- ============================================================ -->
<!-- SECCIÓN 3: DATOS DEL LOTE -->
<!-- ============================================================ -->
<div class="card mb-4" data-modes="ocupante conflicto servicio fraccionamiento">
    <div class="card-header-brown-light">
        <i class="fas fa-ruler-combined"></i>
        <h2 class="mb-0">3. Datos del Lote</h2>
    </div>
    <!-- Arreglo 2:  -->
    <div class="card-body">
        <div class="row g-3">
          <div class="col-md-2">
            <label class="form-label fw-semibold">{{ form.nro_titulo.label }}</label>
            {{ form.nro_titulo }}
            {% if form.nro_titulo.errors %}<div class="text-danger small mt-1">{{ form.nro_titulo.errors }}</div>{% endif %}
          </div>
          <div class="col-md-2">
            <label class="form-label fw-semibold">{{ form.condicion_vivienda.label }}</label>
            {{ form.condicion_vivienda }}
            {% if form.condicion_vivienda.errors %}<div class="text-danger small mt-1">{{ form.condicion_vivienda.errors }}</div>{% endif %}
          </div>
          <div class="col-md-2">
            <label class="form-label fw-semibold">{{ form.condicion_encuestado.label }}</label>
            {{ form.condicion_encuestado }}
            {% if form.condicion_encuestado.errors %}<div class="text-danger small mt-1">{{ form.condicion_encuestado.errors }}</div>{% endif %}
          </div>
          <div class="col-md-4">
            <label class="form-label fw-semibold">{{ form.tipo_lote.label }}</label>
            {{ form.tipo_lote }}
            {% if form.tipo_lote.errors %}<div class="text-danger small mt-1">{{ form.tipo_lote.errors }}</div>{% endif %}
          </div>
          <div class="col-md-4">
            <label class="form-label fw-semibold">{{ form.superficie_ha.label }}</label>
            {{ form.superficie_ha }}
            {% if form.superficie_ha.errors %}<div class="text-danger small mt-1">{{ form.superficie_ha.errors }}</div>{% endif %}
          </div>
          <div class="col-md-4">
            <label class="form-label fw-semibold">{{ form.dimensiones.label }}</label>
            {{ form.dimensiones }}
            {% if form.dimensiones.errors %}<div class="text-danger small mt-1">{{ form.dimensiones.errors }}</div>{% endif %}
          </div>
          <div class="col-md-4">
            <label class="form-label fw-semibold">{{ form.vive_en_lote.label }}</label>
            {{ form.vive_en_lote }}
            {% if form.vive_en_lote.errors %}
            <div class="text-danger small mt-1">{{ form.vive_en_lote.errors }}</div>{% endif %}
          </div>
        </div>
        <!-- Residencia: visible solo si el ocupante no vive en el lote -->
        <div class="row g-3 mt-1" id="residencia-fields-row">
          <div class="col-md-4">
            <label class="form-label fw-semibold">{{ form.parentesco.label }}</label>
            {{ form.parentesco }}
            {% if form.parentesco.errors %}<div class="text-danger small mt-1">{{ form.parentesco.errors }}</div>{% endif %}
          </div>
          <div class="col-md-4">
            <label class="form-label fw-semibold">{{ form.residencia_manzana.label }}</label>
            {{ form.residencia_manzana }}
            {% if form.residencia_manzana.errors %}<div class="text-danger small mt-1">{{ form.residencia_manzana.errors }}</div>{% endif %}
          </div>
          <div class="col-md-4">
            <label class="form-label fw-semibold">{{ form.residencia_lote.label }}</label>
            {{ form.residencia_lote }}
            {% if form.residencia_lote.errors %}<div class="text-danger small mt-1">{{ form.residencia_lote.errors }}</div>{% endif %}
          </div>
        </div>
        <!-- Campo parent_lote solo visible en fraccionamiento -->
        <div class="row g-3 mt-1" data-modes="fraccionamiento" style="display:none;">
          <div class="col-md-4">
            <label class="form-label fw-semibold">{{ form.parent_lote.label }}</label>
            {{ form.parent_lote }}
            {% if form.parent_lote.errors %}<div class="text-danger small mt-1">{{ form.parent_lote.errors }}</div>{% endif %}
          </div>
        </div>
        <!-- Uso del Lote (checkboxes) -->
        <div class="inner-subsection mt-3">
          <label class="form-label fw-semibold mb-2">
            <i class="fas fa-check-square me-1 text-primary"></i>{{ form.uso_lote.label }}
          </label>
          <div class="row row-cols-2 row-cols-md-3 g-2">
            {% for choice in form.uso_lote %}
              <div class="col">
                <div class="form-check">
                  {{ choice.tag }}
                  <label class="form-check-label" for="{{ choice.id_for_label }}">{{ choice.choice_label }}</label>
                </div>
              </div>
            {% endfor %}
          </div>
          {% if form.uso_lote.errors %}
            <div class="text-danger small mt-1">{{ form.uso_lote.errors }}</div>
          {% endif %}
        </div>
      </div>
    </div>
