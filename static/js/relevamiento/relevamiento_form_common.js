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

// ── Dimensión del lote: frente x fondo → dimensiones, superficie_ha, tipo_lote ──
// Cálculo instantáneo en el navegador para la vista previa (los <div> de
// abajo del botón). El valor que realmente se guarda lo recalcula el
// servidor en RelevamientoForm.clean() a partir de frente_aprox/fondo_aprox
// — esto es solo para que el usuario vea el resultado sin recargar la página.
document.addEventListener('DOMContentLoaded', function () {
    const frenteInput = document.getElementById('id_frente_aprox');
    const fondoInput = document.getElementById('id_fondo_aprox');
    const dimensionesInput = document.getElementById('id_dimensiones');
    const superficieInput = document.getElementById('id_superficie_ha');
    const tipoLoteInput = document.getElementById('id_tipo_lote');

    const agregarRow = document.getElementById('agregar-dimension-row');
    const summaryRow = document.getElementById('dimension-summary-row');
    const dimensionDisplay = document.getElementById('dimension-display');
    const superficieDisplay = document.getElementById('superficie-display');
    const tipoLoteDisplay = document.getElementById('tipo-lote-display');
    const guardarBtn = document.getElementById('guardar-dimension-btn');
    const errorMsg = document.getElementById('dimension-modal-error');

    if (!frenteInput || !fondoInput || !guardarBtn) return;

    const TIPO_LOTE_LABELS = { urbano: 'Urbano', quinta: 'Quinta', agricola: 'Agrícola' };

    // Mismos rangos que replica el servidor en RelevamientoForm.clean().
    function calcularTipoLote(superficieHa) {
        if (superficieHa <= 0.25) return 'urbano';
        if (superficieHa <= 2.0) return 'quinta';
        return 'agricola';
    }

    function actualizarVistaDimension() {
        const frente = parseInt(frenteInput.value, 10);
        const fondo = parseInt(fondoInput.value, 10);
        if (!frente || !fondo || frente <= 0 || fondo <= 0) return false;

        const superficieHa = Math.round((frente * fondo / 10000) * 10000) / 10000; // 4 decimales
        const tipoLote = calcularTipoLote(superficieHa);

        if (dimensionesInput) dimensionesInput.value = `${frente}x${fondo}`;
        if (superficieInput) superficieInput.value = superficieHa;
        if (tipoLoteInput) tipoLoteInput.value = tipoLote;

        dimensionDisplay.textContent = `${frente}x${fondo}`;
        superficieDisplay.textContent = superficieHa.toFixed(4);
        tipoLoteDisplay.textContent = TIPO_LOTE_LABELS[tipoLote];

        return true;
    }

    guardarBtn.addEventListener('click', function () {
        const ok = actualizarVistaDimension();
        if (!ok) {
            errorMsg.classList.remove('d-none');
            return;
        }
        errorMsg.classList.add('d-none');
        agregarRow.style.display = 'none';
        summaryRow.style.display = 'contents';  

        guardarBtn.blur();
        bootstrap.Modal.getInstance(document.getElementById('modalDimension')).hide();
    });

    // Si ya había frente/fondo cargado al abrir la página (editando un
    // relevamiento existente), refrescamos la vista previa igual.
    if (frenteInput.value && fondoInput.value) {
        actualizarVistaDimension();
    }
});

// ── Cónyuge (opcional): modal → resumen → editar/eliminar ─────────────────
// El Ocupante ya no necesita JS: el usuario tipea directo en los campos
// reales del form (quien_es_el_ocupante, cedula_ocupante, etc.). El Cónyuge
// se edita vía modal, pero también escribe DIRECTO en los campos ocultos
// reales del Relevamiento — ya no se crea ninguna fila de Miembro acá.
document.addEventListener('DOMContentLoaded', function () {
    const ocSexo = document.getElementById('id_sexo_ocupante');

    const cjNombre = document.getElementById('id_quien_es_el_conyuge');
    const cjCi = document.getElementById('id_cedula_conyuge');
    const cjSexo = document.getElementById('id_sexo_conyuge');
    const cjEstadoCivil = document.getElementById('id_estado_civil_conyuge');

    if (!cjNombre) return; // esta página no tiene sección de cónyuge

    function hayConyugeCargado() {
        return !!cjNombre.value.trim();
    }

    function refrescarResumenConyuge() {
        const addWrap = document.getElementById('conyuge-add-btn-wrap');
        const summary = document.getElementById('conyuge-summary');
        const summaryText = document.getElementById('conyuge-summary-text');
        if (!addWrap || !summary || !summaryText) return;

        if (hayConyugeCargado()) {
            let texto = cjNombre.value;
            if (cjCi.value) texto += ` – CI ${cjCi.value}`;
            const estadoCivilLabel = window.ESTADO_CIVIL_LABELS?.[cjEstadoCivil.value];
            if (estadoCivilLabel) texto += ` – ${estadoCivilLabel}`;

            summaryText.textContent = texto;
            addWrap.classList.add('d-none');
            summary.classList.remove('d-none');
        } else {
            addWrap.classList.remove('d-none');
            summary.classList.add('d-none');
        }
    }

    document.getElementById('modalPersona')?.addEventListener('show.bs.modal', function () {
        document.getElementById('modal_persona_nombre').value = cjNombre.value || '';
        document.getElementById('modal_persona_ci').value = cjCi.value || '';
        document.getElementById('modal_persona_estado_civil').value = cjEstadoCivil.value || '';

        // Sexo del cónyuge: siempre el opuesto del ocupante, sin poder cambiarlo.
        const sexoInput = document.getElementById('modal_persona_sexo');
        const sexoOcupante = ocSexo ? ocSexo.value : '';
        sexoInput.value = sexoOcupante === 'M' ? 'F' : (sexoOcupante === 'F' ? 'M' : '');
        sexoInput.disabled = true;

        document.getElementById('persona-modal-error').classList.add('d-none');
    });

    document.getElementById('guardar-persona-btn')?.addEventListener('click', function () {
        const nombre = document.getElementById('modal_persona_nombre').value.trim();
        if (!nombre) {
            document.getElementById('persona-modal-error').classList.remove('d-none');
            return;
        }

        cjNombre.value = nombre;
        cjCi.value = document.getElementById('modal_persona_ci').value.trim();
        cjSexo.value = document.getElementById('modal_persona_sexo').value;
        cjEstadoCivil.value = document.getElementById('modal_persona_estado_civil').value;

        refrescarResumenConyuge();
        this.blur();
        bootstrap.Modal.getInstance(document.getElementById('modalPersona')).hide();
    });

    document.getElementById('eliminar-conyuge-btn')?.addEventListener('click', function () {
        cjNombre.value = '';
        cjCi.value = '';
        cjSexo.value = '';
        cjEstadoCivil.value = '';
        refrescarResumenConyuge();
    });

    // Estado inicial — por si estamos reabriendo un borrador que ya tenía cónyuge.
    refrescarResumenConyuge();
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
/** Cada "familia" de viviendas tiene su propio grupo de "principal",
 *  independiente de las demás: el ocupante principal es un grupo, y CADA
 *  pretendiente es su propio grupo aparte. */
function getGrupoDeVivienda(checkbox) {
    const pretBlock = checkbox.closest('.pretendiente-block');
    if (pretBlock) return pretBlock;
    return document.getElementById('viviendas-container');
}

// ── "Vivienda principal": solo una a la vez, y si no hay ninguna marcada
//    entre las visibles, se marca la primera automáticamente ──
function asegurarPrincipalPorDefecto() {
    const grupos = new Set();
    document.querySelectorAll('.es-principal-checkbox').forEach(cb => grupos.add(getGrupoDeVivienda(cb)));

    grupos.forEach(grupo => {
        if (!grupo) return;
        const checkboxes = Array.from(grupo.querySelectorAll('.es-principal-checkbox'))
            .filter(cb => cb.closest('.vivienda-block')?.style.display !== 'none');
        if (checkboxes.length === 0) return;
        if (!checkboxes.some(cb => cb.checked)) checkboxes[0].checked = true;
    });
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
/** Contrapartida de eliminarVivienda(): tilda/destilda el checkbox DELETE de
 *  un miembro y muestra/oculta la fila. Mismo patrón que el resto del form. */
function eliminarMiembro(rowEl) {
    const deleteInput = rowEl.querySelector('.miembro-delete-wrapper input[type="checkbox"]');
    if (deleteInput) {
        deleteInput.checked = true;
        rowEl.style.display = 'none';
    } else {
        rowEl.remove();
    }
}
/** Cuenta miembros "reales" (con nombre_miembro cargado) de una vivienda y
 *  actualiza su badge. Mismo criterio que usamos en Cultivos/Ganadería:
 *  no cuenta filas vacías, ni filas ocultas (marcadas para eliminar). */
/** Núcleo compartido: cuenta filas con nombre_miembro cargado dentro de
 *  CUALQUIER tabla de población (ocupante o pretendiente) y pinta el badge. */
function updateMiembrosBadgeGenerico(tbodyId, badgeId) {
    const badge = document.getElementById(badgeId);
    const tbody = document.getElementById(tbodyId);
    if (!badge || !tbody) return;

    const rows = tbody.querySelectorAll('tr.miembro-row');
    let count = 0;
    rows.forEach(row => {
        if (row.style.display === 'none') return;
        const nombreInput = row.querySelector('input[name$="-nombre_miembro"]');
        if (nombreInput && nombreInput.value.trim()) count++;
    });
    badge.textContent = count;
}

function updateMiembrosBadge(vivIdx) {
    updateMiembrosBadgeGenerico(`miembros-forms-${vivIdx}`, `miembros-count-${vivIdx}`);
}
function updateMiembrosBadgePret(pretIdx, vivIdx) {
    updateMiembrosBadgeGenerico(`pret-miembros-forms-${pretIdx}-${vivIdx}`, `pret-miembros-count-${pretIdx}-${vivIdx}`);
}

// Recalcula el badge correspondiente mientras el usuario escribe el nombre
// (delegado: cubre tanto Vivienda del ocupante como Población de Pretendientes).
document.addEventListener('input', function (e) {
    if (!e.target.matches('input[name$="-nombre_miembro"]')) return;
    const tbody = e.target.closest('tbody[id^="miembros-forms-"], tbody[id^="pret-miembros-forms-"]');
    if (!tbody) return;

    if (tbody.id.startsWith('pret-miembros-forms-')) {
        const m = tbody.id.match(/^pret-miembros-forms-(\d+)-(\d+)$/);
        if (m) updateMiembrosBadgePret(m[1], m[2]);
    } else {
        updateMiembrosBadge(tbody.id.replace('miembros-forms-', ''));
    }
});

// Estado inicial de todos los badges al cargar la página.
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[id^="miembros-forms-"]').forEach(tbody => {
        updateMiembrosBadge(tbody.id.replace('miembros-forms-', ''));
    });
    document.querySelectorAll('[id^="pret-miembros-forms-"]').forEach(tbody => {
        const m = tbody.id.match(/^pret-miembros-forms-(\d+)-(\d+)$/);
        if (m) updateMiembrosBadgePret(m[1], m[2]);
    });
});

// ── Botón de borrar en una fila de miembro (delegado, cubre filas clonadas) ──
document.addEventListener('click', function (e) {
  const btn = e.target.closest('.remove-miembro-btn');
  if (!btn) return;
  const row = btn.closest('tr.miembro-row');
  if (!row) return;

  const tbody = row.closest('tbody[id^="miembros-forms-"], tbody[id^="pret-miembros-forms-"]');
  eliminarMiembro(row);
  if (!tbody) return;

  if (tbody.id.startsWith('pret-miembros-forms-')) {
      const m = tbody.id.match(/^pret-miembros-forms-(\d+)-(\d+)$/);
      if (m) updateMiembrosBadgePret(m[1], m[2]);
  } else {
      updateMiembrosBadge(tbody.id.replace('miembros-forms-', ''));
  }
});

// ── Agregar miembro dentro de una vivienda ───────────────────────────────────
document.addEventListener('click', function (e) {
  const btn = e.target.closest('.add-miembro-btn');
  if (!btn) return;
  const vivIdx = btn.dataset.vivIndex;
  const prefix = btn.dataset.prefix;
  const tbody = document.getElementById(`miembros-forms-${vivIdx}`);
  const template = document.getElementById('miembro-empty-row');
  if (!tbody || !template) return;

  const totalInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  if (!totalInput) return;
  const idx = parseInt(totalInput.value);

  const newRow = template.content.firstElementChild.cloneNode(true);
  newRow.querySelectorAll('input, select, textarea, label').forEach(function (element) {
      if (element.name)    element.name    = element.name.replace(/miembros_viv_0-__prefix__/g, `${prefix}-${idx}`);
      if (element.id)      element.id      = element.id.replace(/miembros_viv_0-__prefix__/g, `${prefix}-${idx}`);
      if (element.htmlFor) element.htmlFor = element.htmlFor.replace(/miembros_viv_0-__prefix__/g, `${prefix}-${idx}`);
  });

  const noMiembrosMsg = document.getElementById(`no-miembros-msg-${vivIdx}`);
  if (noMiembrosMsg) noMiembrosMsg.remove();

  tbody.appendChild(newRow);
  totalInput.value = idx + 1;
  btn.dataset.total = idx + 1;
});

// ── Agregar miembro dentro de la vivienda de un pretendiente ─────────────────
document.addEventListener('click', function (e) {
  const btn = e.target.closest('.add-miembro-pret-btn');
  if (!btn) return;
  const pretIdx = btn.dataset.pretIndex;
  const vivIdx = btn.dataset.pretVivIndex;
  const prefix = btn.dataset.prefix;
  const tbody = document.getElementById(`pret-miembros-forms-${pretIdx}-${vivIdx}`);
  const template = document.getElementById('miembro-empty-row');
  if (!tbody || !template) return;

  const totalInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  if (!totalInput) return;
  const idx = parseInt(totalInput.value);

  const newRow = template.content.firstElementChild.cloneNode(true);
  newRow.querySelectorAll('input, select, textarea, label').forEach(function (element) {
      if (element.name)    element.name    = element.name.replace(/miembros_viv_0-__prefix__/g, `${prefix}-${idx}`);
      if (element.id)      element.id      = element.id.replace(/miembros_viv_0-__prefix__/g, `${prefix}-${idx}`);
      if (element.htmlFor) element.htmlFor = element.htmlFor.replace(/miembros_viv_0-__prefix__/g, `${prefix}-${idx}`);
  });

  const noMiembrosMsg = document.getElementById(`no-miembros-msg-pret-${pretIdx}-${vivIdx}`);
  if (noMiembrosMsg) noMiembrosMsg.remove();

  tbody.appendChild(newRow);
  totalInput.value = idx + 1;
  btn.dataset.total = idx + 1;
  updateMiembrosBadgePret(pretIdx, vivIdx);
});

// ── Agregar vivienda adicional (modo ocupante / fraccionamiento) ─────────────

document.getElementById('add-vivienda-btn')?.addEventListener('click', function () {
  const vivPrefix = 'viviendas';
  const totalInput = document.getElementById(`id_${vivPrefix}-TOTAL_FORMS`);
  if (!totalInput) return;
  const newVivIdx = parseInt(totalInput.value);

  const emptyViv = document.getElementById('viviendas-empty');
  if (!emptyViv) return;

  // El HTML de "viviendas-empty" trae nombres "viviendas-__prefix__-campo".
  // Reemplazamos __prefix__ SOLO por el índice (el prefijo "viviendas-" ya
  // está incluido en el nombre original).
  const vivHtml = emptyViv.innerHTML.replace(/__prefix__/g, newVivIdx);
  const miemPrefix = `miembros_viv_${newVivIdx}`;

  // Una vivienda nueva arranca SIN miembros cargados (TOTAL_FORMS = 0).
  // El usuario los agrega con el botón "Agregar miembro", que clona el
  // mismo <template id="miembro-empty-row"> que usa el resto del formulario.
  const mgmtHtml = `
    <input type="hidden" name="${miemPrefix}-TOTAL_FORMS" id="id_${miemPrefix}-TOTAL_FORMS" value="0">
    <input type="hidden" name="${miemPrefix}-INITIAL_FORMS" id="id_${miemPrefix}-INITIAL_FORMS" value="0">
    <input type="hidden" name="${miemPrefix}-MIN_NUM_FORMS" id="id_${miemPrefix}-MIN_NUM_FORMS" value="0">
    <input type="hidden" name="${miemPrefix}-MAX_NUM_FORMS" id="id_${miemPrefix}-MAX_NUM_FORMS" value="1000">`;

  // El botón "Cargar/Actualizar datos del ocupante" SOLO existe en la
  // Vivienda 0 — las viviendas adicionales solo tienen "Agregar miembro".
  const botonCargarOcupanteHtml = newVivIdx === 0
    ? `<button type="button" class="btn btn-sm btn-outline-info" id="cargar-ocupante-btn-0">
         <i class="fas fa-user-check me-1"></i>Cargar datos del ocupante
       </button>`
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
    <button type="button" class="mini-accordion-header">
      <i class="fas fa-users me-1"></i> Población
      <span class="badge bg-secondary ms-2" id="miembros-count-${newVivIdx}">0</span>
    </button>
    <div class="mini-accordion-body d-none" id="miembros-block-${newVivIdx}" data-viv-index="${newVivIdx}">
      ${mgmtHtml}
      <div class="table-responsive">
        <table class="beautiful-table align-middle mb-0" id="miembros-table-${newVivIdx}">
          <thead>
            <tr class="text-center">
              <th>Nombre y Apellido</th>
              <th>Cedula</th>
              <th>Edad</th>
              <th>Sexo</th>
              <th>Estado civil</th>
              <th>Relación</th>
              <th>Escolaridad</th>
              <th>Grado/Año</th>
              <th>Acción</th>
            </tr>
          </thead>
          <tbody id="miembros-forms-${newVivIdx}">
            <tr id="no-miembros-msg-${newVivIdx}">
              <td colspan="9" class="text-muted text-center">Sin miembros registrados.</td>
            </tr>
          </tbody>
        </table>
      </div>
      ${botonCargarOcupanteHtml}
      <button type="button" class="btn btn-sm btn-outline-secondary add-miembro-btn mt-1"
              data-viv-index="${newVivIdx}" data-prefix="${miemPrefix}" data-total="0">
        <i class="fas fa-user-plus me-1"></i>Agregar miembro
      </button>
    </div>`;

  document.getElementById('viviendas-container').appendChild(div);
  totalInput.value = newVivIdx + 1;
  asegurarPrincipalPorDefecto();

  // El botón recién creado (si es la Vivienda 0) arranca oculto por defecto
  // arriba; lo sincronizamos con el estado real de vive_en_lote apenas se crea.
  if (typeof actualizarBotonCargarOcupante === 'function') actualizarBotonCargarOcupante();

});
// ── "Cargar/Actualizar datos del ocupante" en Población (Vivienda 0) ──
// Lee los datos de Ocupante/Cónyuge directo del Relevamiento (ya guardados
// en Parte 1 — ver window.DATOS_OCUPANTE_CONYUGE) y los copia/actualiza en
// la tabla de Población de la Vivienda 0.
function copiarPersonaAPoblacion(parentesco, datos) {
    if (!datos || !datos.nombre) return;

    const tbody = document.getElementById('miembros-forms-0');
    if (!tbody) return;

    let filaViv = Array.from(tbody.querySelectorAll('tr.miembro-row')).find(row => {
        const par = row.querySelector('input[name$="-relacion_con_lote"]');
        return par && par.value === parentesco;
    });

    if (!filaViv) {
        const tplMiembro = document.getElementById('miembro-empty-row');
        const totalMiembroInput = document.getElementById('id_miembros_viv_0-TOTAL_FORMS');
        if (!tplMiembro || !totalMiembroInput) return;
        const idx = parseInt(totalMiembroInput.value, 10);
        const newRow = tplMiembro.content.firstElementChild.cloneNode(true);
        newRow.querySelectorAll('input, select, textarea, label').forEach(el => {
            if (el.name)    el.name    = el.name.replace(/miembros_viv_0-__prefix__/g, `miembros_viv_0-${idx}`);
            if (el.id)      el.id      = el.id.replace(/miembros_viv_0-__prefix__/g, `miembros_viv_0-${idx}`);
            if (el.htmlFor) el.htmlFor = el.htmlFor.replace(/miembros_viv_0-__prefix__/g, `miembros_viv_0-${idx}`);
        });
        document.getElementById('no-miembros-msg-0')?.remove();
        tbody.appendChild(newRow);
        totalMiembroInput.value = idx + 1;
        filaViv = newRow;
    }

    filaViv.querySelector('input[name$="-nombre_miembro"]').value = datos.nombre;
    filaViv.querySelector('input[name$="-ci_miembro"]').value = datos.ci;
    filaViv.querySelector('select[name$="-sexo_miembro"]').value = datos.sexo;
    filaViv.querySelector('select[name$="-estado_civil_miembro"]').value = datos.estado_civil;
    const parInput = filaViv.querySelector('input[name$="-relacion_con_lote"]');
    if (parInput) parInput.value = parentesco;
}

document.addEventListener('click', function (e) {
    if (!e.target.closest('#cargar-ocupante-btn-0')) return;
    const datos = window.DATOS_OCUPANTE_CONYUGE || {};
    copiarPersonaAPoblacion('Ocupante', datos.ocupante);
    copiarPersonaAPoblacion('Cónyuge', datos.conyuge);
    updateMiembrosBadge('0');
    document.getElementById('miembros-block-0')?.classList.remove('d-none');
    e.target.closest('#cargar-ocupante-btn-0').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
});
// ── Auto-crear Vivienda 1 al cargar la página si el contenedor está vacío ──
// (En el wizard nuevo, esta página ya no pasa por actualizarVisibilidadViviendas,
//  así que nos aseguramos acá de que exista al menos un bloque de vivienda.)
document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('viviendas-container');
    if (container && container.querySelectorAll('.vivienda-block').length === 0) {
        document.getElementById('add-vivienda-btn')?.click();
    }
});

// ── Agregar pretendiente (con su propia vivienda y población anidadas) ───────

document.getElementById('add-pretendiente-btn')?.addEventListener('click', function () {
  const prefix = this.dataset.prefix;
  const totalInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  const emptyPret = document.getElementById('pretendientes-empty');
  const emptyViv = document.getElementById('pret-vivienda-empty-template');
  if (!totalInput || !emptyPret) return;
  const newIdx = parseInt(totalInput.value);

  const vivPrefix = `viviendas_pret_${newIdx}`;
  const miemPrefix = `miembros_pret_${newIdx}_viv_0`;

  const vivMgmtHtml = `
    <input type="hidden" name="${vivPrefix}-TOTAL_FORMS" id="id_${vivPrefix}-TOTAL_FORMS" value="1">
    <input type="hidden" name="${vivPrefix}-INITIAL_FORMS" id="id_${vivPrefix}-INITIAL_FORMS" value="0">
    <input type="hidden" name="${vivPrefix}-MIN_NUM_FORMS" id="id_${vivPrefix}-MIN_NUM_FORMS" value="0">
    <input type="hidden" name="${vivPrefix}-MAX_NUM_FORMS" id="id_${vivPrefix}-MAX_NUM_FORMS" value="1000">`;

  // FIX: una vivienda/pretendiente nuevo arranca sin miembros cargados.
  const miemMgmtHtml = `
    <input type="hidden" name="${miemPrefix}-TOTAL_FORMS" id="id_${miemPrefix}-TOTAL_FORMS" value="0">
    <input type="hidden" name="${miemPrefix}-INITIAL_FORMS" id="id_${miemPrefix}-INITIAL_FORMS" value="0">
    <input type="hidden" name="${miemPrefix}-MIN_NUM_FORMS" id="id_${miemPrefix}-MIN_NUM_FORMS" value="0">
    <input type="hidden" name="${miemPrefix}-MAX_NUM_FORMS" id="id_${miemPrefix}-MAX_NUM_FORMS" value="1000">`;

  // ⚠️ PENDIENTE (ver nota debajo): sigo sin el fragmento real de
  // "pret-vivienda-empty-template", así que este .replace() puede tener
  // el mismo bug de doble-prefijo que identificamos hace unas pasadas.
  const vivHtml = emptyViv
    ? emptyViv.innerHTML.replace(/viviendas_pret_0-__prefix__/g, `${vivPrefix}-0`)
    : '';

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
            <button type="button" class="mini-accordion-header">
              <i class="fas fa-users me-1"></i> Población
              <span class="badge bg-secondary ms-2" id="pret-miembros-count-${newIdx}-0">0</span>
            </button>
            <div class="mini-accordion-body d-none" id="pret-miembros-block-${newIdx}-0">
            ${miemMgmtHtml}
            <div class="table-responsive">
              <table class="beautiful-table align-middle mb-0" id="pret-miembros-table-${newIdx}-0">
                <thead>
                  <tr class="text-center">
                    <th>Nombre y Apellido</th>
                    <th>Cedula</th>
                    <th>Edad</th>
                    <th>Sexo</th>
                    <th>Estado civil</th>
                    <th>Relación</th>
                    <th>Escolaridad</th>
                    <th>Grado/Año</th>
                    <th>Acción</th>
                  </tr>
                </thead>
                <tbody id="pret-miembros-forms-${newIdx}-0">
                  <tr id="no-miembros-msg-pret-${newIdx}-0">
                    <td colspan="9" class="text-muted text-center">Sin miembros registrados.</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <button type="button" class="btn btn-sm btn-outline-secondary add-miembro-pret-btn mt-1"
                    data-pret-index="${newIdx}" data-pret-viv-index="0" data-prefix="${miemPrefix}" data-total="0">
              <i class="fas fa-user-plus me-1"></i>Agregar miembro
            </button>
          </div>
        </div>
      </div>
    </div>`;

  document.getElementById('pretendientes-container').appendChild(div);
  totalInput.value = newIdx + 1;
  this.dataset.total = newIdx + 1;
  asegurarPrincipalPorDefecto(); 
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
  const tbody      = document.getElementById(containerId);
  const template   = document.getElementById('miembro-empty-row');
  const totalInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
  if (!tbody || !template || !totalInput) return;

  const idx = parseInt(totalInput.value);
  const newRow = template.content.firstElementChild.cloneNode(true);
  newRow.querySelectorAll('input, select, textarea, label').forEach(function (element) {
      if (element.name)    element.name    = element.name.replace(/miembros_viv_0-__prefix__/g, `${prefix}-${idx}`);
      if (element.id)      element.id      = element.id.replace(/miembros_viv_0-__prefix__/g, `${prefix}-${idx}`);
      if (element.htmlFor) element.htmlFor = element.htmlFor.replace(/miembros_viv_0-__prefix__/g, `${prefix}-${idx}`);
  });

  tbody.appendChild(newRow);
  totalInput.value = idx + 1;
  addBtn.dataset.total = idx + 1;

  // Rellenar los campos del nuevo miembro con los datos del cónyuge
  const get = name => newRow.querySelector(`[name="${prefix}-${idx}-${name}"]`);
  if (get('nombre_miembro'))       get('nombre_miembro').value       = nombre;
  if (get('ci_miembro'))           get('ci_miembro').value           = ci;
  if (get('sexo_miembro'))         get('sexo_miembro').value         = sexo;
  if (get('estado_civil_miembro')) get('estado_civil_miembro').value = estadoCivil;
  if (get('parentesco'))           get('parentesco').value           = 'Cónyuge';
  
  if (target === '0') {
    updateMiembrosBadge('0');
  } else {
    const pretIdx = target.replace('pret_', '');
    updateMiembrosBadgePret(pretIdx, '0');
  }

  bootstrap.Modal.getInstance(document.getElementById('modalConyuge')).hide();
  tbody.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Instituciones/Servicios: modal → lista de tarjetas → editar/eliminar ──
document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('instituciones-container');
    const template = document.getElementById('institucion-empty-row');
    const totalInput = document.getElementById('id_instituciones-TOTAL_FORMS');
    const listEl = document.getElementById('instituciones-lista');
    if (!container || !template || !totalInput || !listEl) return;

    function escapeHtml(texto) {
        const div = document.createElement('div');
        div.textContent = texto || '';
        return div.innerHTML;
    }

    function crearFilaInstitucion() {
        const idx = parseInt(totalInput.value, 10);
        const div = document.createElement('div');
        div.innerHTML = template.innerHTML.replace(/__prefix__/g, idx);
        const fila = div.firstElementChild;
        container.appendChild(div);
        totalInput.value = idx + 1;
        return fila;
    }

    function refrescarListaInstituciones() {
        listEl.innerHTML = '';
        const filas = Array.from(container.querySelectorAll('.institucion-row'));
        let count = 0;

        filas.forEach((fila, idx) => {
            const del = fila.querySelector('input[name$="-DELETE"]');
            if (del && del.checked) return;
            const nombre = fila.querySelector('input[name$="-nombre_servicio"]').value;
            if (!nombre) return;

            count++;
            const ruc = fila.querySelector('input[name$="-ruc_servicio"]').value;
            const desc = fila.querySelector('textarea[name$="-descripcion_servicio"]').value;
            const descCorta = desc.length > 80 ? desc.slice(0, 80) + '…' : desc;

            const card = document.createElement('div');
            card.className = 'border rounded p-2 mb-2 d-flex justify-content-between align-items-start';
            card.innerHTML = `
              <div>
                <div class="fw-semibold">${escapeHtml(nombre)}</div>
                ${ruc ? `<div class="small text-muted">RUC: ${escapeHtml(ruc)}</div>` : ''}
                ${descCorta ? `<div class="small">${escapeHtml(descCorta)}</div>` : ''}
              </div>
              <div class="ms-2 flex-shrink-0">
                <button type="button" class="btn btn-sm btn-outline-secondary editar-institucion-btn"
                        data-bs-toggle="modal" data-bs-target="#modalInstitucion" data-idx="${idx}" title="Editar">
                  <i class="fas fa-pencil-alt"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-danger eliminar-institucion-btn" data-idx="${idx}" title="Eliminar">
                  <i class="fas fa-trash"></i>
                </button>
              </div>`;
            listEl.appendChild(card);
        });

        document.getElementById('instituciones-vacio').style.display = count === 0 ? '' : 'none';
    }

    document.getElementById('modalInstitucion')?.addEventListener('show.bs.modal', function (event) {
        const idxAttr = event.relatedTarget?.dataset.idx;
        document.getElementById('institucion-modal-error')?.classList.add('d-none');

        if (idxAttr !== undefined) {
            // Modo edición: precargar con lo que hay en esa fila.
            const idx = parseInt(idxAttr, 10);
            window.institucionEditIndex = idx;
            const fila = container.querySelectorAll('.institucion-row')[idx];
            document.getElementById('modal_institucion_nombre').value = fila?.querySelector('input[name$="-nombre_servicio"]')?.value || '';
            document.getElementById('modal_institucion_ruc').value = fila?.querySelector('input[name$="-ruc_servicio"]')?.value || '';
            document.getElementById('modal_institucion_descripcion').value = fila?.querySelector('textarea[name$="-descripcion_servicio"]')?.value || '';
        } else {
            // Modo agregar: todo vacío.
            window.institucionEditIndex = null;
            document.getElementById('modal_institucion_nombre').value = '';
            document.getElementById('modal_institucion_ruc').value = '';
            document.getElementById('modal_institucion_descripcion').value = '';
        }
    });

    document.getElementById('guardar-institucion-btn')?.addEventListener('click', function () {
        const nombre = document.getElementById('modal_institucion_nombre').value.trim();
        if (!nombre) {
            document.getElementById('institucion-modal-error').classList.remove('d-none');
            return;
        }
        const ruc = document.getElementById('modal_institucion_ruc').value.trim();
        const descripcion = document.getElementById('modal_institucion_descripcion').value.trim();

        const fila = (window.institucionEditIndex === null || window.institucionEditIndex === undefined)
            ? crearFilaInstitucion()
            : container.querySelectorAll('.institucion-row')[window.institucionEditIndex];
        if (!fila) return;

        fila.querySelector('input[name$="-nombre_servicio"]').value = nombre;
        fila.querySelector('input[name$="-ruc_servicio"]').value = ruc;
        fila.querySelector('textarea[name$="-descripcion_servicio"]').value = descripcion;

        refrescarListaInstituciones();
        this.blur();
        bootstrap.Modal.getInstance(document.getElementById('modalInstitucion')).hide();
    });

    document.addEventListener('click', function (e) {
        const delBtn = e.target.closest('.eliminar-institucion-btn');
        if (!delBtn) return;
        const idx = parseInt(delBtn.dataset.idx, 10);
        const fila = container.querySelectorAll('.institucion-row')[idx];
        if (!fila) return;
        const delInput = fila.querySelector('input[name$="-DELETE"]');
        if (delInput) delInput.checked = true; else fila.remove();
        refrescarListaInstituciones();
    });

    refrescarListaInstituciones(); // estado inicial, por si ya hay instituciones guardadas
});

// ── Inicialización común ─────────────────────────────────────────────────────
//3. DATOS DEL LOTE 
document.addEventListener('DOMContentLoaded', function() {
    const viveCheck = document.getElementById('{{ form.vive_en_lote.id_for_label }}');
    const viveLabel = document.getElementById('label-vive-en-lote');
    if (viveCheck && viveLabel) {
        viveCheck.addEventListener('change', function() {
            viveLabel.textContent = this.checked ? 'Reside' : 'No reside';
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
        ? 'Reside'
        : 'No reside';
    }

  function toggleResidencia() {
    if (residenciaRow) {residenciaRow.style.display =(viveCheck && viveCheck.checked) ? 'none' : '';}
       actualizarLabelViveEnLote();
       actualizarBotonCargarOcupante();
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
  // Actualiza el estado del botón "Cargar datos del ocupante" según vive_en_lote
  window.actualizarBotonCargarOcupante = function () {
     if (!viveCheck) return;
    const btn = document.getElementById('cargar-ocupante-btn-0');
    if (!btn) return;
    btn.style.display = (viveCheck && viveCheck.checked) ? '' : 'none';
  };

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
        valor === 'en_construccion'||
        valor === 'desocupada'
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


  /** Contrapartida de eliminarVivienda(): destilda el DELETE y vuelve a mostrar el bloque.
  *  Se usa cuando la sección pasa de oculta a visible, para "resucitar" el
  *  bloque que se había limpiado y ocultado anteriormente. */
    function restaurarVivienda(blockEl) {
      const deleteInput = blockEl.querySelector(':scope > .vivienda-delete-wrapper input[type="checkbox"]');
      if (deleteInput) deleteInput.checked = false;
        blockEl.style.display = '';
    }

  // Agregar listeners para la regla automática de 'en construccion'
  // ── Mostrar/ocultar la sección "Viviendas del Lote" ──────────────────────────
  // Solo se muestra cuando: tipo_registro == 'ocupante' Y condicion_vivienda
  // está en ['presente', 'ausente', 'en_construccion']. En cualquier otro caso
  // (sin_vivienda, servicio) no hay una vivienda física que describir.
    function actualizarVisibilidadViviendas() {
        const viviendasSection = document.getElementById('viviendas-section');
        if (!viviendasSection) return;
        if (!document.getElementById('id_tipo_registro')) return;

        const tipoRegistro = document.getElementById('id_tipo_registro')?.value;
        const condicionViviendaVal = document.getElementById('id_condicion_vivienda')?.value;
        const CONDICIONES_CON_VIVIENDA = ['presente', 'ausente', 'en_construccion', 'desocupada'];
        const mostrar = tipoRegistro === 'ocupante' && CONDICIONES_CON_VIVIENDA.includes(condicionViviendaVal);

        viviendasSection.style.display = mostrar ? '' : 'none';

        const bloques = document.querySelectorAll('#viviendas-container .vivienda-block');
        
        if (!mostrar) {
            // No corresponde vivienda: limpiamos y marcamos para borrar.
            bloques.forEach(block => eliminarVivienda(block));
        } else {
            // Corresponde vivienda: restauramos cualquier bloque que se hubiera
            // limpiado/ocultado antes, para que el usuario lo vea listo para cargar.
            bloques.forEach(block => restaurarVivienda(block));
            const visibles = document.querySelectorAll('#viviendas-container .vivienda-block:not([style*="display: none"])');
            if (visibles.length === 0) {
                document.getElementById('add-vivienda-btn')?.click();
            }
            asegurarPrincipalPorDefecto();
        }
        window.actualizarBotonCargarOcupante?.();
    }

    document.addEventListener('change', function (e) {
        if (!e.target.matches('.es-principal-checkbox')) return;
        const grupo = getGrupoDeVivienda(e.target);
        if (e.target.checked) {
            grupo.querySelectorAll('.es-principal-checkbox').forEach(cb => {
                if (cb !== e.target) cb.checked = false;
            });
        } else {
            e.target.checked = true; // no se permite quedar sin ninguna principal
        }
    });
    asegurarPrincipalPorDefecto();

  // Se recalcula cada vez que cambia alguno de los dos campos que lo determinan
  document.getElementById('id_tipo_registro')?.addEventListener('change', actualizarVisibilidadViviendas);
  document.getElementById('id_condicion_vivienda')?.addEventListener('change', actualizarVisibilidadViviendas);

  // Estado inicial (por ejemplo, al editar un relevamiento que ya tiene datos)
  actualizarVisibilidadViviendas();
  actualizarBotonCargarOcupante();
  
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

        const newRow = template.content.firstElementChild.cloneNode(true);

        newRow.querySelectorAll('input, select, textarea, label').forEach(function (element) {
            if (element.name)    element.name    = element.name.replace(/__prefix__/g, currentIndex);
            if (element.id)      element.id      = element.id.replace(/__prefix__/g, currentIndex);
            if (element.htmlFor) element.htmlFor = element.htmlFor.replace(/__prefix__/g, currentIndex);
        });

        const noCultivosMsg = document.getElementById('no-cultivos-msg');
        if (noCultivosMsg) noCultivosMsg.remove();

        tbody.appendChild(newRow);
        totalFormsInput.value = currentIndex + 1;
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
// índice correcto, y contar en el badge solo las filas con tipo_ganaderia elegido.
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {

    const addBtn = document.getElementById('add-ganaderia-btn');
    const tbody = document.getElementById('ganaderia-body');
    const template = document.getElementById('ganaderia-empty-row');

    if (!addBtn || !tbody || !template) {
        console.warn('Formset de ganadería: elementos no encontrados.');
        return;
    }

    const prefix = addBtn.dataset.prefix; // "ganaderia"
    const totalFormsInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);

    if (!totalFormsInput) {
        console.warn(`No se encontró id_${prefix}-TOTAL_FORMS`);
        return;
    }

    // Cuenta solo las filas visibles cuyo select de tipo_ganaderia tenga un valor.
    // El campo del modelo se llama "tipo_ganaderia" (ver ProduccionGanaderaForm),
    // no "tipo_ganaderia" — con ese nombre el contador nunca encontraba nada.
    // Cuenta solo las filas visibles cuyo select de tipo_ganaderia tenga un valor.
    function updateBadge() {
        const badge = document.getElementById('ganaderia-count');
        if (!badge) return;

        const rows = tbody.querySelectorAll('tr.ganaderia-row');
        let count = 0;

        rows.forEach(row => {
            if (row.style.display === 'none') return;

            // FIX: el campo real se llama tipo_ganaderia, no tipo_ganado
            const selectTipoGanaderia = row.querySelector('select[name$="-tipo_ganaderia"]');
            if (selectTipoGanaderia && selectTipoGanaderia.value) {
                count++;
            }
        });

        badge.textContent = count;
    }

    // Agregar ganado
    addBtn.addEventListener('click', function () {
        const currentIndex = parseInt(totalFormsInput.value, 10);
        if (Number.isNaN(currentIndex)) {
            console.error(`${prefix}-TOTAL_FORMS no contiene un número válido.`);
            return;
        }

        const newRow = template.content.firstElementChild.cloneNode(true);

        // Mismo fix que cultivos: el <template> ya trae el prefijo real
        // ("ganaderia-__prefix__-campo"), solo reemplazamos por el índice.
        newRow.querySelectorAll('input, select, textarea, label').forEach(function (element) {
            if (element.name)    element.name    = element.name.replace(/__prefix__/g, currentIndex);
            if (element.id)      element.id      = element.id.replace(/__prefix__/g, currentIndex);
            if (element.htmlFor) element.htmlFor = element.htmlFor.replace(/__prefix__/g, currentIndex);
        });

        const noGanaderiaMsg = document.getElementById('no-ganaderia-msg');
        if (noGanaderiaMsg) noGanaderiaMsg.remove();

        tbody.appendChild(newRow);
        totalFormsInput.value = currentIndex + 1;
    });

    // Recalcular badge cuando eligen tipo_ganaderia (delegación de eventos)
    tbody.addEventListener('change', function (event) {
        if (event.target.matches('select[name$="-tipo_ganaderia"]')) {
            updateBadge();
        }
    });

    // Eliminar ganado
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

    updateBadge();
});