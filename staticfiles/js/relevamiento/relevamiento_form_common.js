// ── Toggle genérico del mini-acordeón (Vivienda / Equipamiento / Población) ──
// Delegado en document: funciona también para bloques agregados dinámicamente.
document.addEventListener('click', function (e) {
    const header = e.target.closest('.mini-accordion-header');
    if (!header) return;
    const body = header.nextElementSibling;
    if (body && body.classList.contains('mini-accordion-body')) {
        body.classList.toggle('d-none');
    }
});

// ── Limpia los campos visibles de un bloque (vivienda + equipamiento + población) ──
// No toca los campos ocultos (FKs, ids de formset, TOTAL_FORMS, etc.)
function limpiarCamposBloque(blockEl) {
    blockEl.querySelectorAll('input, select, textarea').forEach(el => {
        if (el.type === 'hidden') return;
        if (el.type === 'checkbox' || el.type === 'radio') {
            el.checked = false;
        } else if (el.tagName === 'SELECT') {
            el.selectedIndex = 0;
        } else {
            el.value = '';
        }
    });
}

// ── Elimina una vivienda: limpia sus campos y la marca para borrar (o la
//    saca del DOM si es una vivienda nueva que todavía no se guardó) ──
function eliminarVivienda(blockEl) {
    limpiarCamposBloque(blockEl);

    // Buscamos el DELETE que es HIJO DIRECTO del bloque, para no confundirlo
    // con el DELETE de algún miembro anidado adentro de la vivienda.
    const deleteInput = blockEl.querySelector(':scope > .vivienda-delete-wrapper input[type="checkbox"]');
    if (deleteInput) {
        deleteInput.checked = true;
        blockEl.style.display = 'none';
    } else {
        blockEl.remove();
    }
}

// ── "Vivienda principal": solo una a la vez, y si no hay ninguna marcada
//    entre las visibles, se marca la primera automáticamente ──
function asegurarPrincipalPorDefecto() {
    const checkboxes = Array.from(document.querySelectorAll('.es-principal-checkbox'))
        .filter(cb => cb.closest('.vivienda-block')?.style.display !== 'none');
    if (checkboxes.length === 0) return;
    if (!checkboxes.some(cb => cb.checked)) {
        checkboxes[0].checked = true;
    }
}

// ── Utilidades de formset dinámico compartidas por los 4 modos de relevamiento ──
/** Actualiza id/name/for de un elemento reemplazando __prefix__ o el índice viejo. */
function updateIndex(el, oldPrefix, newPrefix) {
  const re = new RegExp(oldPrefix.replace(/[-[\]{}()*+?.,\\^$|#\s]/g, '\\$&'), 'g');
  ['id', 'name', 'htmlFor'].forEach(attr => {
    if (el[attr]) el[attr] = el[attr].replace(re, newPrefix);
  });
}

/** Clona la plantilla vacía de un formset simple y la agrega al contenedor. */
function addFlatForm(containerEl, emptyHtml, prefix) {
  const totalInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  if (!totalInput) return;
  const idx = parseInt(totalInput.value);
  const html = emptyHtml.replace(/__prefix__/g, `${prefix}-${idx}`);
  const div = document.createElement('div');
  div.className = 'border rounded p-3 mb-2';
  div.innerHTML = `<div class="d-flex justify-content-between align-items-center mb-2">
    <h6 class="mb-0">Elemento ${idx + 1}</h6>
    <button type="button" class="btn btn-sm btn-outline-danger remove-block-btn"><i class="fas fa-trash"></i></button>
  </div>` + html;
  containerEl.appendChild(div);
  totalInput.value = idx + 1;
}

/** Marca el formulario para eliminación usando el checkbox DELETE del formset. */
function markForDelete(blockEl) {
  const deleteInput = blockEl.querySelector('input[id$="-DELETE"]');
  if (deleteInput) {
    deleteInput.checked = true;
    blockEl.style.display = 'none';
  } else {
    blockEl.remove();
  }
}

// ── Botones de agregar para formsets planos (cultivos, ganadería, etc.) ──────

document.querySelectorAll('.add-block-btn').forEach(btn => {
  btn.addEventListener('click', function () {
    const containerId = this.dataset.container;
    const prefix = this.dataset.prefix;
    const emptyDivId = `${prefix}-empty`;
    const emptyDiv = document.getElementById(emptyDivId);
    const container = document.getElementById(containerId);
    if (!emptyDiv || !container) return;
    addFlatForm(container, emptyDiv.innerHTML, prefix);
  });
});

// ── Eliminar cualquier bloque ────────────────────────────────────────────────

document.addEventListener('click', function (e) {
    const vivBtn = e.target.closest('.remove-vivienda-btn');
    if (vivBtn) {
        const block = vivBtn.closest('.vivienda-block');
        if (block) {
            eliminarVivienda(block);
            asegurarPrincipalPorDefecto(); // por si se borró la que era principal
        }
        return;
    }
    const genericBtn = e.target.closest('.remove-block-btn');
    if (genericBtn) {
        markForDelete(genericBtn.closest('[class*="-block"], .border'));
    }
});
// ── Agregar miembro dentro de una vivienda ───────────────────────────────────

document.addEventListener('click', function (e) {
  const btn = e.target.closest('.add-miembro-btn');
  if (!btn) return;
  const vivIdx = btn.dataset.vivIndex;
  const prefix = btn.dataset.prefix;
  const container = document.getElementById(`miembros-forms-${vivIdx}`);
  const emptyTemplate = document.getElementById('miembro-empty-template');
  if (!container || !emptyTemplate) return;

  const totalInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  if (!totalInput) return;
  const idx = parseInt(totalInput.value);
  const html = emptyTemplate.innerHTML.replace(/__prefix__/g, `${prefix}-${idx}`);
  const div = document.createElement('div');
  div.className = 'miembro-form-row border rounded p-2 mb-2';
  div.innerHTML = html;
  container.appendChild(div);
  totalInput.value = idx + 1;
  btn.dataset.total = idx + 1;
});

// ── Agregar miembro dentro de la vivienda de un pretendiente ─────────────────

document.addEventListener('click', function (e) {
  const btn = e.target.closest('.add-miembro-pret-btn');
  if (!btn) return;
  const prefix = btn.dataset.prefix;
  const container = document.getElementById(`pret-miembros-forms-${btn.dataset.pretIndex}-${btn.dataset.pretVivIndex}`);
  const emptyTemplate = document.getElementById('miembro-empty-template');
  if (!container || !emptyTemplate) return;

  const totalInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  if (!totalInput) return;
  const idx = parseInt(totalInput.value);
  const html = emptyTemplate.innerHTML.replace(/__prefix__/g, `${prefix}-${idx}`);
  const div = document.createElement('div');
  div.className = 'miembro-form-row border rounded p-2 mb-2';
  div.innerHTML = html;
  container.appendChild(div);
  totalInput.value = idx + 1;
  btn.dataset.total = idx + 1;
});

// ── Agregar vivienda adicional (modo ocupante / fraccionamiento) ─────────────

document.getElementById('add-vivienda-btn')?.addEventListener('click', function () {
  const vivPrefix = 'viviendas';
  const totalInput = document.getElementById(`id_${vivPrefix}-TOTAL_FORMS`);
  if (!totalInput) return;
  const newVivIdx = parseInt(totalInput.value);

  const emptyViv = document.getElementById('viviendas-empty');
  const emptyMiem = document.getElementById('miembro-empty-template');
  if (!emptyViv) return;

  const vivHtml = emptyViv.innerHTML.replace(/__prefix__/g, `${vivPrefix}-${newVivIdx}`);
  const miemPrefix = `miembros_viv_${newVivIdx}`;

  const mgmtHtml = `
    <input type="hidden" name="${miemPrefix}-TOTAL_FORMS" id="id_${miemPrefix}-TOTAL_FORMS" value="1">
    <input type="hidden" name="${miemPrefix}-INITIAL_FORMS" id="id_${miemPrefix}-INITIAL_FORMS" value="0">
    <input type="hidden" name="${miemPrefix}-MIN_NUM_FORMS" id="id_${miemPrefix}-MIN_NUM_FORMS" value="0">
    <input type="hidden" name="${miemPrefix}-MAX_NUM_FORMS" id="id_${miemPrefix}-MAX_NUM_FORMS" value="1000">`;

  const miemHtml = emptyMiem
    ? emptyMiem.innerHTML.replace(/__prefix__/g, `${miemPrefix}-0`)
    : '';

  const div = document.createElement('div');
  div.className = 'vivienda-block border rounded p-3 mb-3';
  div.dataset.vivIndex = newVivIdx;
  div.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h5 class="mb-0"><i class="fas fa-home me-1"></i>Vivienda ${newVivIdx + 1}</h5>
      <button type="button" class="btn btn-sm btn-outline-danger remove-vivienda-btn"><i class="fas fa-trash"></i></button>
    </div>
    ${vivHtml}
    <div class="miembros-block mt-3 ps-3 border-start border-primary" id="miembros-block-${newVivIdx}">
      <h6 class="text-primary mb-2"><i class="fas fa-users me-1"></i>Miembros de esta vivienda</h6>
      ${mgmtHtml}
      <div class="miembros-forms-container" id="miembros-forms-${newVivIdx}">
        ${miemHtml ? `<div class="miembro-form-row border rounded p-2 mb-2">${miemHtml}</div>` : ''}
      </div>
      <button type="button" class="btn btn-sm btn-outline-secondary add-miembro-btn mt-1"
              data-viv-index="${newVivIdx}" data-prefix="${miemPrefix}" data-total="1">
        <i class="fas fa-user-plus me-1"></i>Agregar miembro
      </button>
    </div>`;

  document.getElementById('viviendas-container').appendChild(div);
  totalInput.value = newVivIdx + 1;
  asegurarPrincipalPorDefecto();
});

// ── Agregar pretendiente (con su propia vivienda y población anidadas) ───────

document.getElementById('add-pretendiente-btn')?.addEventListener('click', function () {
  const prefix = this.dataset.prefix;
  const totalInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  const emptyPret = document.getElementById('pretendientes-empty');
  const emptyViv = document.getElementById('pret-vivienda-empty-template');
  const emptyMiem = document.getElementById('miembro-empty-template');
  if (!totalInput || !emptyPret) return;
  const newIdx = parseInt(totalInput.value);

  const vivPrefix = `viviendas_pret_${newIdx}`;
  const miemPrefix = `miembros_pret_${newIdx}_viv_0`;

  const vivMgmtHtml = `
    <input type="hidden" name="${vivPrefix}-TOTAL_FORMS" id="id_${vivPrefix}-TOTAL_FORMS" value="1">
    <input type="hidden" name="${vivPrefix}-INITIAL_FORMS" id="id_${vivPrefix}-INITIAL_FORMS" value="0">
    <input type="hidden" name="${vivPrefix}-MIN_NUM_FORMS" id="id_${vivPrefix}-MIN_NUM_FORMS" value="0">
    <input type="hidden" name="${vivPrefix}-MAX_NUM_FORMS" id="id_${vivPrefix}-MAX_NUM_FORMS" value="1000">`;
  const miemMgmtHtml = `
    <input type="hidden" name="${miemPrefix}-TOTAL_FORMS" id="id_${miemPrefix}-TOTAL_FORMS" value="1">
    <input type="hidden" name="${miemPrefix}-INITIAL_FORMS" id="id_${miemPrefix}-INITIAL_FORMS" value="0">
    <input type="hidden" name="${miemPrefix}-MIN_NUM_FORMS" id="id_${miemPrefix}-MIN_NUM_FORMS" value="0">
    <input type="hidden" name="${miemPrefix}-MAX_NUM_FORMS" id="id_${miemPrefix}-MAX_NUM_FORMS" value="1000">`;

  const vivHtml = emptyViv ? emptyViv.innerHTML.replace(/__prefix__/g, `${vivPrefix}-0`) : '';
  const miemHtml = emptyMiem ? emptyMiem.innerHTML.replace(/__prefix__/g, `${miemPrefix}-0`) : '';

  const div = document.createElement('div');
  div.className = 'pretendiente-block border rounded p-3 mb-3';
  div.dataset.pretIndex = newIdx;
  div.innerHTML = `
    <div class="d-flex justify-content-between align-items-center mb-2">
      <h6 class="mb-0">Pretendiente ${newIdx + 1}</h6>
      <button type="button" class="btn btn-sm btn-outline-danger remove-block-btn"><i class="fas fa-trash"></i></button>
    </div>
    ${emptyPret.innerHTML.replace(/__prefix__/g, `${prefix}-${newIdx}`)}
    <button type="button" class="btn btn-sm btn-outline-secondary mb-2"
            data-bs-toggle="modal" data-bs-target="#modalConyuge" data-conyuge-target="pret_${newIdx}">
      <i class="fas fa-user-friends me-1"></i> Agregar Cónyuge
    </button>
    <div class="pretendiente-viviendas-block mt-2 ps-3 border-start border-secondary" data-pret-index="${newIdx}">
      <h6 class="text-secondary mb-2"><i class="fas fa-home me-1"></i>Vivienda del pretendiente</h6>
      ${vivMgmtHtml}
      <div class="pret-viviendas-forms-container" id="pret-viviendas-forms-${newIdx}">
        <div class="border rounded p-2 mb-2" data-pret-viv-index="0">
          ${vivHtml}
          <div class="ps-3 border-start border-primary" id="pret-miembros-block-${newIdx}-0">
            <h6 class="text-primary small mb-2"><i class="fas fa-users me-1"></i>Población</h6>
            ${miemMgmtHtml}
            <div class="miembros-forms-container" id="pret-miembros-forms-${newIdx}-0">
              ${miemHtml ? `<div class="miembro-form-row border rounded p-2 mb-2">${miemHtml}</div>` : ''}
            </div>
            <button type="button" class="btn btn-sm btn-outline-secondary add-miembro-pret-btn mt-1"
                    data-pret-index="${newIdx}" data-pret-viv-index="0" data-prefix="${miemPrefix}" data-total="1">
              <i class="fas fa-user-plus me-1"></i>Agregar miembro
            </button>
          </div>
        </div>
      </div>
    </div>`;

  document.getElementById('pretendientes-container').appendChild(div);
  totalInput.value = newIdx + 1;
  this.dataset.total = newIdx + 1;
});

// ── Cónyuge: agrega el cónyuge como miembro de la primera vivienda (o de la del pretendiente) ──

function guardarConyuge() {
  const nombre = document.getElementById('modal_conyuge_nombre').value.trim();
  const ci     = document.getElementById('modal_conyuge_ci').value.trim();
  const sexo   = document.getElementById('modal_conyuge_sexo').value;
  const estadoCivil = document.getElementById('modal_conyuge_estado_civil')?.value || '';

  if (!nombre) {
    document.getElementById('modal_conyuge_nombre').classList.add('is-invalid');
    document.getElementById('modal_conyuge_nombre').focus();
    return;
  }
  document.getElementById('modal_conyuge_nombre').classList.remove('is-invalid');

  const target = window.currentConyugeTarget || '0';
  let addBtn;
  if (target === '0') {
    addBtn = document.querySelector('.add-miembro-btn[data-viv-index="0"]');
  } else {
    const pretIdx = target.replace('pret_', '');
    addBtn = document.querySelector(`.add-miembro-pret-btn[data-pret-index="${pretIdx}"][data-pret-viv-index="0"]`);
  }
  if (!addBtn) {
    bootstrap.Modal.getInstance(document.getElementById('modalConyuge')).hide();
    return;
  }

  const prefix     = addBtn.dataset.prefix;
  const containerId = target === '0'
    ? 'miembros-forms-0'
    : `pret-miembros-forms-${target.replace('pret_', '')}-0`;
  const container  = document.getElementById(containerId);
  const emptyTpl   = document.getElementById('miembro-empty-template');
  const totalInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  if (!container || !emptyTpl || !totalInput) return;

  const idx  = parseInt(totalInput.value);
  const html = emptyTpl.innerHTML.replace(/__prefix__/g, `${prefix}-${idx}`);
  const div  = document.createElement('div');
  div.className = 'miembro-form-row border rounded p-2 mb-2';
  div.innerHTML = html;
  container.appendChild(div);
  totalInput.value   = idx + 1;
  addBtn.dataset.total = idx + 1;
  // Rellenar los campos del nuevo miembro con los datos del cónyuge
  const get = name => div.querySelector(`[name="${prefix}-${idx}-${name}"]`);
  if (get('nombre'))       get('nombre').value       = nombre;
  if (get('ci'))           get('ci').value           = ci;
  if (get('sexo'))         get('sexo').value         = sexo;
  if (get('estado_civil')) get('estado_civil').value = estadoCivil;
  if (get('parentesco'))   get('parentesco').value   = 'Cónyuge';

  bootstrap.Modal.getInstance(document.getElementById('modalConyuge')).hide();
  container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Inicialización común ─────────────────────────────────────────────────────
//3. DATOS DEL LOTE 
document.addEventListener('DOMContentLoaded', function() {
    const viveCheck = document.getElementById('{{ form.vive_en_lote.id_for_label }}');
    const viveLabel = document.getElementById('label-vive-en-lote');
    if (viveCheck && viveLabel) {
        viveCheck.addEventListener('change', function() {
            viveLabel.textContent = this.checked ? 'Vive en el lote' : 'No vive en el lote';
        });
    }
});

document.addEventListener('DOMContentLoaded', function () {
  const viveCheck = document.getElementById('id_vive_en_lote');
  const viveLabel = document.getElementById('label-vive-en-lote');
  const residenciaRow = document.getElementById('residencia-fields-row');
  const condicionVivienda = document.getElementById('id_condicion_vivienda');
  const container = document.getElementById('viviendas-container');
    
  function actualizarLabelViveEnLote() {
    if (!viveCheck || !viveLabel) return;
      viveLabel.textContent = viveCheck.checked
        ? 'Vive en el lote'
        : 'No vive en el lote';
    }

  function toggleResidencia() {
    if (residenciaRow) {residenciaRow.style.display =(viveCheck && viveCheck.checked) ? 'none' : '';}
       actualizarLabelViveEnLote();
  }

  if (viveCheck) {viveCheck.addEventListener('change', toggleResidencia);
  }

  function actualizarCondicion() {
    if (tipoSelect.value === 'servicio') {
        condicionSelect.value = 'servicio';
        condicionSelect.disabled = true;
        // agregar mensaje dinámico...
    } else {
        condicionSelect.disabled = false;
        // quitar mensaje...
    }
    // Disparar evento change para que las reglas de vive_en_lote se activen
    condicionSelect.dispatchEvent(new Event('change'));
  }

  // Regla automática: condicion_vivienda == 'presente' fuerza vive_en_lote = true
  // 'sin vivienda' fuerza vive_en_lote = False
  // 'en construccion' fuerza vive_en_lote = False
  function aplicarReglaCondicionVivienda() {

    if (!condicionVivienda || !viveCheck) return;
    const valor = condicionVivienda.value;

    if (valor === 'presente') {// Vive en el lote
        viveCheck.checked = true;

    } else if (
        valor === 'sin_vivienda' ||
        valor === 'en_construccion'
    ) { // No vive en el lote
        viveCheck.checked = false;
    }
      toggleResidencia();
  }

  if (condicionVivienda) {
      condicionVivienda.addEventListener(
          'change',
          aplicarReglaCondicionVivienda
      );
  }
  aplicarReglaCondicionVivienda();
  toggleResidencia();

  // Agregar listeners para las reglas automáticas de condicion_vivienda
  if (condicionVivienda) condicionVivienda.addEventListener('change', aplicarReglaCondicionVivienda);
  aplicarReglaCondicionVivienda();
  // Agregar listeners para la regla automática de 'sin vivienda'

  // Agregar listeners para la regla automática de 'en construccion'
  // ── Mostrar/ocultar la sección "Viviendas del Lote" ──────────────────────────
  // Solo se muestra cuando: tipo_registro == 'ocupante' Y condicion_vivienda
  // está en ['presente', 'ausente', 'en_construccion']. En cualquier otro caso
  // (sin_vivienda, servicio) no hay una vivienda física que describir.
  function actualizarVisibilidadViviendas() {
      const viviendasSection = document.getElementById('viviendas-section');
      if (!viviendasSection) return;

      const tipoRegistro = document.getElementById('id_tipo_registro')?.value;
      const condicionVivienda = document.getElementById('id_condicion_vivienda')?.value;
      const CONDICIONES_CON_VIVIENDA = ['presente', 'ausente', 'en_construccion'];
      const mostrar = tipoRegistro === 'ocupante' && CONDICIONES_CON_VIVIENDA.includes(condicionVivienda);

      if (!mostrar) {
          // Sección oculta: limpiamos y marcamos para borrar cada vivienda visible
          document.querySelectorAll('#viviendas-container .vivienda-block').forEach(block => {
              if (block.style.display !== 'none') eliminarVivienda(block);
          });
      }

      viviendasSection.style.display = mostrar ? '' : 'none';
  }

  if (container) {
        // Comportamiento tipo radio-button: al tildar una, se destildan las demás.
        container.addEventListener('change', function (e) {
            if (!e.target.matches('.es-principal-checkbox')) return;
            if (e.target.checked) {
                document.querySelectorAll('.es-principal-checkbox').forEach(cb => {
                    if (cb !== e.target) cb.checked = false;
                });
            } else {
                // No se permite quedar sin ninguna principal.
                e.target.checked = true;
            }
        });
    }
    asegurarPrincipalPorDefecto();

  // Se recalcula cada vez que cambia alguno de los dos campos que lo determinan
  document.getElementById('id_tipo_registro')?.addEventListener('change', actualizarVisibilidadViviendas);
  document.getElementById('id_condicion_vivienda')?.addEventListener('change', actualizarVisibilidadViviendas);

  // Estado inicial (por ejemplo, al editar un relevamiento que ya tiene datos)
  actualizarVisibilidadViviendas();
  
  // Preseleccionar sexo opuesto al abrir el modal de cónyuge (según el target que lo abrió)
  document.getElementById('modalConyuge')?.addEventListener('show.bs.modal', function (event) {
    window.currentConyugeTarget = event.relatedTarget?.dataset.conyugeTarget || '0';
    const sexoInput = window.currentConyugeTarget === '0'
      ? document.getElementById('id_sexo_ocupante')
      : document.querySelector(`[name$="-${window.currentConyugeTarget.replace('pret_', '')}-sexo"]`);
    const conyugeSexo = document.getElementById('modal_conyuge_sexo');
    if (conyugeSexo) conyugeSexo.value = (sexoInput?.value === 'M') ? 'F' : 'M';
    document.getElementById('modal_conyuge_nombre').value = '';
    document.getElementById('modal_conyuge_nombre').classList.remove('is-invalid');
    document.getElementById('modal_conyuge_ci').value = '';
  });
});


// ── Sincronización automática de la condición de vivienda según el tipo de relevamiento ──
document.addEventListener('DOMContentLoaded', function() {
    const tipoSelect = document.querySelector('#id_tipo_registro');
    const condicionSelect = document.querySelector('#id_condicion_vivienda');
    
    // Si los campos no existen, salir (por si acaso)
    if (!tipoSelect || !condicionSelect) return;

    // Buscar el contenedor del campo (el div.col-md-2) para mostrar mensaje dinámico
    const container = condicionSelect.closest('.col-md-2') || condicionSelect.parentElement;
    let dynamicHelp = null;

    function actualizarCondicion() {
        if (tipoSelect.value === 'servicio') {
            // Forzar valor y deshabilitar el campo
            condicionSelect.value = 'servicio';
            condicionSelect.disabled = true;
            // Añadir mensaje informativo (opcional)
            if (!dynamicHelp) {
                dynamicHelp = document.createElement('small');
                dynamicHelp.className = 'text-muted d-block mt-1';
                dynamicHelp.textContent = 'Condición fijada automáticamente a "Servicio"';
                container.appendChild(dynamicHelp);
            }
        } else {
            // Habilitar el campo para que el usuario elija
            condicionSelect.disabled = false;
            // Eliminar mensaje dinámico si existe
            if (dynamicHelp) {
                dynamicHelp.remove();
                dynamicHelp = null;
            }
            // Opcional: limpiar el valor o dejarlo como está
            // condicionSelect.value = '';
        }
    }

    // Escuchar cambios en el selector de tipo
    tipoSelect.addEventListener('change', actualizarCondicion);
    
    // Ejecutar al cargar la página para sincronizar estado inicial
    actualizarCondicion();
});

// ─────────────────────────────────────────────────────────────────────────────
// MANEJO DE CULTIVOS
//
// Qué hace este bloque:
// 1. Cuando el usuario clickea "Agregar cultivo", clona la fila oculta del
//    <template>, le pone el índice correcto en name/id, y la inserta en la tabla.
// 2. Cuenta en el badge SOLO las filas que ya tienen un tipo_cultivo elegido
//    (no cuenta filas vacías).
// 3. Al eliminar una fila (tacho), la marca para borrar (si ya existía en la
//    base) o la saca del DOM directamente (si es nueva), y actualiza el badge.
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {

    const addBtn = document.getElementById('add-cultivo-btn');
    const tbody = document.getElementById('cultivos-body');
    const template = document.getElementById('cultivos-empty-row');

    if (!addBtn || !tbody || !template) {
        console.warn('Formset de cultivos: elementos no encontrados.');
        return;
    }

    // Prefijo del formset de Django (ej: "cultivos"). Django arma los nombres
    // de los campos como "cultivos-0-tipo_cultivo", "cultivos-1-tipo_cultivo", etc.
    const prefix = addBtn.dataset.prefix;

    // Este input oculto le dice a Django cuántos formularios se están enviando.
    // Es OBLIGATORIO mantenerlo actualizado o el formset no procesa las filas nuevas.
    const totalFormsInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);

    if (!totalFormsInput) {
        console.warn(`No se encontró id_${prefix}-TOTAL_FORMS`);
        return;
    }

    // -------------------------------------------------------------------------
    // Contar cultivos "reales" (con tipo_cultivo seleccionado) y pintar el badge
    // -------------------------------------------------------------------------
    // OJO: esto NO cuenta filas. Cuenta cuántos <select name="...-tipo_cultivo">
    // tienen un valor distinto de vacío, y que además estén visibles (una fila
    // marcada para eliminar se oculta con display:none, no debe sumar).
    function updateBadge() {
        const badge = document.getElementById('cultivo-count');
        if (!badge) return;

        const rows = tbody.querySelectorAll('tr.cultivo-row');
        let count = 0;

        rows.forEach(row => {
            if (row.style.display === 'none') return; // marcada para eliminar

            const selectTipoCultivo = row.querySelector('select[name$="-tipo_cultivo"]');
            if (selectTipoCultivo && selectTipoCultivo.value) {
                count++;
            }
        });

        badge.textContent = count;
    }

    // -------------------------------------------------------------------------
    // Agregar cultivo (clic en el botón)
    // -------------------------------------------------------------------------
    addBtn.addEventListener('click', function () {

        const currentIndex = parseInt(totalFormsInput.value, 10);
        if (Number.isNaN(currentIndex)) {
            console.error(`${prefix}-TOTAL_FORMS no contiene un número válido.`);
            return;
        }

        // Clonamos la fila del <template>. Como ahora usamos empty_form de
        // Django, los <select> ya vienen con TODAS las opciones cargadas.
        const newRow = template.content.firstElementChild.cloneNode(true);

        // Reemplazamos "__prefix__" por el índice real (0, 1, 2...) en cada
        // input/select/label de la fila clonada, para que Django sepa a qué
        // formulario del formset pertenece cada campo.
        newRow.querySelectorAll('input, select, textarea, label').forEach(function (element) {
            if (element.name)    element.name    = element.name.replace(/__prefix__/g, `${prefix}-${currentIndex}`);
            if (element.id)      element.id      = element.id.replace(/__prefix__/g, `${prefix}-${currentIndex}`);
            if (element.htmlFor) element.htmlFor = element.htmlFor.replace(/__prefix__/g, `${prefix}-${currentIndex}`);
        });

        // Sacamos el mensaje "Sin cultivos registrados" si estaba
        const noCultivosMsg = document.getElementById('no-cultivos-msg');
        if (noCultivosMsg) noCultivosMsg.remove();

        tbody.appendChild(newRow);

        // Avisamos a Django que ahora hay un formulario más
        totalFormsInput.value = currentIndex + 1;

        // Fila nueva = sin tipo_cultivo elegido todavía, así que el badge
        // no cambia hasta que el usuario seleccione algo (ver listener de abajo)
    });

    // -------------------------------------------------------------------------
    // Recalcular el badge cuando el usuario elige un tipo_cultivo
    // -------------------------------------------------------------------------
    // Usamos delegación de eventos (escuchamos en el tbody, no en cada select)
    // porque las filas se crean dinámicamente después de que cargó la página.
    tbody.addEventListener('change', function (event) {
        if (event.target.matches('select[name$="-tipo_cultivo"]')) {
            updateBadge();
        }
    });

    // -------------------------------------------------------------------------
    // Eliminar cultivo (tacho)
    // -------------------------------------------------------------------------
    tbody.addEventListener('click', function (event) {
        const btn = event.target.closest('.remove-block-btn');
        if (!btn) return;

        const row = btn.closest('tr.cultivo-row');
        if (!row) return;

        const deleteInput = row.querySelector('input[name$="-DELETE"]');
        if (deleteInput) {
            // Fila que ya existía guardada en la base: no la borramos del DOM,
            // marcamos el checkbox DELETE del formset y la ocultamos.
            // Django se encarga de eliminarla al guardar el formulario.
            deleteInput.checked = true;
            row.style.display = 'none';
        } else {
            // Fila recién agregada (todavía no guardada): la sacamos directo.
            row.remove();
        }

        updateBadge();
    });

    // -------------------------------------------------------------------------
    // Inicialización: contar lo que ya venía cargado al abrir la página
    // (por ejemplo, si estás editando un Relevamiento existente)
    // -------------------------------------------------------------------------
    updateBadge();
});

// ─────────────────────────────────────────────────────────────────────────────
// MANEJO DE GANADERÍA
//
// Misma lógica que Cultivos: clonar fila oculta, renombrar campos con el
// índice correcto, y contar en el badge solo las filas con tipo_ganado elegido.
// ─────────────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', function () {

    const addBtn = document.getElementById('add-ganaderia-btn');
    const tbody = document.getElementById('ganaderia-body');
    const template = document.getElementById('ganaderia-empty-row');

    if (!addBtn || !tbody || !template) {
        console.warn('Formset de ganaderia: elementos no encontrados.');
        return;
    }

    const prefix = addBtn.dataset.prefix; // "ganaderia"
    const totalFormsInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);

    if (!totalFormsInput) {
        console.warn(`No se encontró id_${prefix}-TOTAL_FORMS`);
        return;
    }

    // Cuenta solo las filas visibles cuyo select de tipo_ganado tenga un valor.
    function updateBadge() {
        const badge = document.getElementById('ganado-count');
        if (!badge) return;

        const rows = tbody.querySelectorAll('tr.ganado-row');
        let count = 0;

        rows.forEach(row => {
            if (row.style.display === 'none') return;

            const selectTipoGanado = row.querySelector('select[name$="-tipo_ganado"]');
            if (selectTipoGanado && selectTipoGanado.value) {
                count++;
            }
        });

        badge.textContent = count;
    }
    // -------------------------------------------------------------------------
    // Contar cultivos "reales" (con tipo_cultivo seleccionado) y pintar el badge
    // -------------------------------------------------------------------------
    // OJO: esto NO cuenta filas. Cuenta cuántos <select name="...-tipo_cultivo">
    // tienen un valor distinto de vacío, y que además estén visibles (una fila
    // marcada para eliminar se oculta con display:none, no debe sumar).
    function updateBadge() {
        const badge = document.getElementById('ganaderia-count');
        if (!badge) return;

        const rows = tbody.querySelectorAll('tr.ganaderia-row');
        let count = 0;

        rows.forEach(row => {
            if (row.style.display === 'none') return; // marcada para eliminar

            const selectTipoganaderia = row.querySelector('select[name$="-tipo_ganaderia"]');
            if (selectTipoganaderia && selectTipoganaderia.value) {
                count++;
            }
        });

        badge.textContent = count;
    }

    // Agregar ganaderia
    addBtn.addEventListener('click', function () {
        const currentIndex = parseInt(totalFormsInput.value, 10);
        if (Number.isNaN(currentIndex)) {
            console.error(`${prefix}-TOTAL_FORMS no contiene un número válido.`);
            return;
        }

        const newRow = template.content.firstElementChild.cloneNode(true);

        newRow.querySelectorAll('input, select, textarea, label').forEach(function (element) {
            if (element.name)    element.name    = element.name.replace(/__prefix__/g, `${prefix}-${currentIndex}`);
            if (element.id)      element.id      = element.id.replace(/__prefix__/g, `${prefix}-${currentIndex}`);
            if (element.htmlFor) element.htmlFor = element.htmlFor.replace(/__prefix__/g, `${prefix}-${currentIndex}`);
        });

        const noganaderiaMsg = document.getElementById('no-ganaderia-msg');
        if (noganaderiaMsg) noganaderiaMsg.remove();

        tbody.appendChild(newRow);
        totalFormsInput.value = currentIndex + 1;
    });

    // Recalcular badge cuando eligen tipo_ganaderia (delegación de eventos)
    tbody.addEventListener('change', function (event) {
        if (event.target.matches('select[name$="-tipo_ganaderia"]')) {
            updateBadge();
        }
    });

    // Eliminar ganaderia
    tbody.addEventListener('click', function (event) {
        const btn = event.target.closest('.remove-block-btn');
        if (!btn) return;

        const row = btn.closest('tr.ganaderia-row');
        if (!row) return;

        const deleteInput = row.querySelector('input[name$="-DELETE"]');
        if (deleteInput) {
            deleteInput.checked = true;
            row.style.display = 'none';
        } else {
            row.remove();
        }

        updateBadge();
    });

    // Contar lo que ya venía cargado al abrir la página
    updateBadge();
});