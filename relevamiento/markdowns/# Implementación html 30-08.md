# Documento de Implementación para Formulario de Relevamiento

**Versión:** 1.1  
**Fecha:** 2026-08-30  
**Autor:** Jose Dominguez

---
Me gustaria adaptar el funcionamiento de "Formulario de Relevamiento Prueba" html con el formulario_relevamiento.html

el ejemplo que me gustaria que sigas es este, y ademas quiero que mantengas el estilo css de fomulario_relevamiento.html, fijate que todo encaje y este ordenado.

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Formulario de Relevamiento Prueba</title>
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome para iconos -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #f5f7fa; }
        .container { max-width: 1200px; }
        .section-card { background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
        .section-header { background: #e9ecef; padding: 10px 15px; border-radius: 10px 10px 0 0; font-weight: 600; }
        .btn-circle { width: 30px; height: 30px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; }
        .modal-body { max-height: 70vh; overflow-y: auto; }
        .img-thumbnail { max-width: 100px; margin: 5px; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container py-4">
        <h2 class="mb-4"><i class="fas fa-clipboard-list me-2"></i>Formulario de Relevamiento de Lotes</h2>

        <!-- Selector de Modo -->
        <div class="row mb-4">
            <div class="col-12">
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

        <!-- Contenido dinámico según modo -->
        <div id="mode-content">
            <!-- Se rellena con JavaScript -->
        </div>
    </div>

    <!-- Modales globales -->
    <!-- Modal Cónyuge -->
    <div class="modal fade" id="modalConyuge" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Datos del Cónyuge</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">Nombre del cónyuge</label>
                        <input type="text" class="form-control" id="conyugeNombre">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">CI del cónyuge</label>
                        <input type="text" class="form-control" id="conyugeCI">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Sexo (por defecto opuesto)</label>
                        <select class="form-select" id="conyugeSexo">
                            <option value="M">Masculino</option>
                            <option value="F">Femenino</option>
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button class="btn btn-primary" onclick="guardarConyuge()">Guardar</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal Características de Vivienda -->
    <div class="modal fade" id="modalCaracteristicas" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Características de la Vivienda</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Materiales</h6>
                            <div class="form-check"><input class="form-check-input" type="checkbox" id="carParedLadrillo"> <label class="form-check-label">Pared de ladrillo</label></div>
                            <div class="form-check"><input class="form-check-input" type="checkbox" id="carParedMadera"> <label class="form-check-label">Pared de madera</label></div>
                            <div class="form-check"><input class="form-check-input" type="checkbox" id="carTechoChapa"> <label class="form-check-label">Techo de chapa</label></div>
                            <div class="form-check"><input class="form-check-input" type="checkbox" id="carTechoTeja"> <label class="form-check-label">Techo de teja</label></div>
                        </div>
                        <div class="col-md-6">
                            <h6>Servicios</h6>
                            <div class="form-check"><input class="form-check-input" type="checkbox" id="carAguaCorriente"> <label class="form-check-label">Agua corriente</label></div>
                            <div class="form-check"><input class="form-check-input" type="checkbox" id="carLuz"> <label class="form-check-label">Luz eléctrica</label></div>
                            <div class="form-check"><input class="form-check-input" type="checkbox" id="carPozo"> <label class="form-check-label">Pozo ciego</label></div>
                            <div class="form-check"><input class="form-check-input" type="checkbox" id="carDesague"> <label class="form-check-label">Desagüe cloacal</label></div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button class="btn btn-primary" onclick="guardarCaracteristicas()">Guardar</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal Equipamiento de Vivienda -->
    <div class="modal fade" id="modalEquipamiento" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Equipamiento de la Vivienda</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="form-check"><input class="form-check-input" type="checkbox" id="equipHeladera"> <label class="form-check-label">Heladera</label></div>
                    <div class="form-check"><input class="form-check-input" type="checkbox" id="equipCocina"> <label class="form-check-label">Cocina</label></div>
                    <div class="form-check"><input class="form-check-input" type="checkbox" id="equipTV"> <label class="form-check-label">Televisor</label></div>
                    <div class="form-check"><input class="form-check-input" type="checkbox" id="equipComputadora"> <label class="form-check-label">Computadora</label></div>
                    <div class="form-check"><input class="form-check-input" type="checkbox" id="equipAire"> <label class="form-check-label">Aire acondicionado</label></div>
                    <div class="form-check"><input class="form-check-input" type="checkbox" id="equipVehiculo"> <label class="form-check-label">Vehículo</label></div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button class="btn btn-primary" onclick="guardarEquipamiento()">Guardar</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal Residencia -->
    <div class="modal fade" id="modalResidencia" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Información de Residencia</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">Manzana de residencia</label>
                        <input type="text" class="form-control" id="resManzana">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Lote de residencia</label>
                        <input type="text" class="form-control" id="resLote">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Ocupante del lote donde reside</label>
                        <input type="text" class="form-control" id="resOcupante">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Parentesco</label>
                        <select class="form-select" id="resParentesco">
                            <option>Familiar</option><option>Amigo</option><option>Conocido</option><option>Otro</option>
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button class="btn btn-primary" onclick="guardarResidencia()">Guardar</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal Fotos (simulación) -->
    <div class="modal fade" id="modalFotos" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Agregar Fotos de la Vivienda</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <input type="file" id="inputFotos" multiple accept="image/*" class="form-control mb-3">
                    <div id="previewFotos" class="d-flex flex-wrap"></div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button class="btn btn-primary" onclick="guardarFotos()">Guardar</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Bootstrap JS y dependencias -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Estado global
        let currentMode = 'ocupante';
        let currentTargetId = null; // Para saber a qué bloque pertenece la acción (ej. pretendiente)
        let currentConyugeTarget = null;
        let currentViviendaTarget = null;
        let pretendientesCount = 0;
        let subLotesCount = 0;
        let viviendasAdicionales = {}; // { parentId: [ids] }

        // Almacenamiento temporal (localStorage)
        function saveState() {
            // No implementado completamente, solo simulación
        }

        function switchMode(mode) {
            currentMode = mode;
            document.querySelectorAll('[data-mode]').forEach(btn => {
                btn.classList.remove('active');
                if (btn.dataset.mode === mode) btn.classList.add('active');
            });
            renderModeContent();
        }

        function renderModeContent() {
            const container = document.getElementById('mode-content');
            container.innerHTML = '';
            if (currentMode === 'ocupante') {
                container.appendChild(createOcupanteBlock());
            } else if (currentMode === 'conflicto') {
                container.appendChild(createConflictoBlock());
            } else if (currentMode === 'servicio') {
                container.appendChild(createServicioBlock());
            } else if (currentMode === 'fraccionamiento') {
                container.appendChild(createFraccionamientoBlock());
            }
            // Re-inicializar tooltips si fuera necesario
        }

        // ========== BLOQUES DE CONSTRUCCIÓN ==========
        function createGeographicSection() {
            const div = document.createElement('div');
            div.className = 'section-card';
            div.innerHTML = `
                <div class="section-header"><i class="fas fa-map-marker-alt me-2"></i>Datos Geográficos</div>
                <div class="p-3">
                    <div class="row g-3">
                        <div class="col-md-4">
                            <label class="form-label">Departamento</label>
                            <input type="text" class="form-control" placeholder="Departamento">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Distrito</label>
                            <input type="text" class="form-control" placeholder="Distrito">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Colonia</label>
                            <input type="text" class="form-control" placeholder="Colonia">
                        </div>
                    </div>
                </div>
            `;
            return div;
        }

        function createPersonFields(prefix, includeConyuge = false, sexoId = null) {
            const wrapper = document.createElement('div');
            wrapper.className = 'p-3';
            wrapper.innerHTML = `
                <div class="row g-3">
                    <div class="col-md-3">
                        <label class="form-label">Nombre</label>
                        <input type="text" class="form-control" placeholder="Nombre completo">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">CI</label>
                        <input type="text" class="form-control" placeholder="Cédula">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Sexo</label>
                        <select class="form-select">
                            <option value="M">Masculino</option>
                            <option value="F">Femenino</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label">Estado Civil</label>
                        <select class="form-select">
                            <option>Soltero/a</option>
                            <option>Casado/a</option>
                            <option>Unión libre</option>
                            <option>Viudo/a</option>
                            <option>Divorciado/a</option>
                        </select>
                    </div>
                    ${includeConyuge ? `
                    <div class="col-md-2 d-flex align-items-end">
                        <button class="btn btn-sm btn-outline-secondary w-100" onclick="openConyugeModal(this)" data-prefix="${prefix}">
                            <i class="fas fa-user-friends me-1"></i> Cónyuge
                        </button>
                    </div>` : ''}
                </div>
            `;
            return wrapper;
        }

        function createViviendaConditionSection(targetId, prefix) {
            const section = document.createElement('div');
            section.className = 'p-3 border-top';
            section.innerHTML = `
                <label class="form-label fw-bold">Condición de la vivienda</label>
                <select class="form-select mb-3" onchange="handleCondicionVivienda(this, '${targetId}', '${prefix}')">
                    <option value="">Seleccione...</option>
                    <option value="presente">Presente</option>
                    <option value="ausente">Ausente</option>
                    <option value="construccion">En construcción</option>
                    <option value="sin_vivienda">Sin vivienda</option>
                </select>
                <div class="vivienda-extra"></div>
            `;
            return section;
        }

        function handleCondicionVivienda(selectEl, targetId, prefix) {
            const extraDiv = selectEl.parentElement.querySelector('.vivienda-extra');
            extraDiv.innerHTML = '';
            const cond = selectEl.value;
            if (cond === 'presente' || cond === 'ausente') {
                extraDiv.innerHTML = `
                    <div class="alert alert-info">
                        <button class="btn btn-sm btn-outline-primary me-2" onclick="openCaracteristicasModal('${targetId}')">
                            <i class="fas fa-home me-1"></i> Características
                        </button>
                        ${cond === 'presente' ? `<button class="btn btn-sm btn-outline-primary me-2" onclick="openEquipamientoModal('${targetId}')">
                            <i class="fas fa-plug me-1"></i> Equipamiento
                        </button>` : ''}
                    </div>
                `;
            } else if (cond === 'construccion') {
                extraDiv.innerHTML = `
                    <div class="alert alert-info">
                        <button class="btn btn-sm btn-outline-primary" onclick="openCaracteristicasModal('${targetId}')">
                            <i class="fas fa-home me-1"></i> Características
                        </button>
                    </div>
                `;
            } else if (cond === 'sin_vivienda') {
                extraDiv.innerHTML = `
                    <div class="alert alert-warning">
                        <button class="btn btn-sm btn-outline-secondary" onclick="openResidenciaModal('${targetId}')">
                            <i class="fas fa-info-circle me-1"></i> Información de residencia
                        </button>
                    </div>
                `;
            }
            // Si es presente, mostrar checkbox vive en lote
            if (cond === 'presente') {
                const viveCheck = document.createElement('div');
                viveCheck.className = 'form-check mt-2';
                viveCheck.innerHTML = `
                    <input class="form-check-input" type="checkbox" id="vive_${targetId}" checked onchange="toggleResidenciaInfo(this, '${targetId}')">
                    <label class="form-check-label">Vive en el lote</label>
                `;
                extraDiv.appendChild(viveCheck);
            }
        }

        function toggleResidenciaInfo(checkbox, targetId) {
            // Si desmarca, mostrar botón para residencia
            const extraDiv = checkbox.closest('.vivienda-extra');
            if (!checkbox.checked) {
                const btnRes = document.createElement('button');
                btnRes.className = 'btn btn-sm btn-outline-secondary ms-3';
                btnRes.innerHTML = '<i class="fas fa-info-circle me-1"></i> Agregar residencia';
                btnRes.onclick = () => openResidenciaModal(targetId);
                extraDiv.appendChild(btnRes);
            } else {
                // Eliminar botón si existe
                const btns = extraDiv.querySelectorAll('button');
                btns.forEach(b => { if (b.textContent.includes('Agregar residencia')) b.remove(); });
            }
        }

        function createPoblacionSection(targetId, prefix) {
            const section = document.createElement('div');
            section.className = 'p-3 border-top';
            section.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="mb-0"><i class="fas fa-users me-2"></i>Registro de Población</h6>
                    <button class="btn btn-sm btn-success" onclick="addPoblacionRow('${targetId}')">
                        <i class="fas fa-plus me-1"></i> Agregar persona
                    </button>
                </div>
                <div class="table-responsive">
                    <table class="table table-bordered table-sm" id="tabla_poblacion_${targetId}">
                        <thead>
                            <tr>
                                <th>Orden</th><th>Nombres</th><th>Cédula</th><th>Edad</th><th>Relación</th><th>Grado</th><th></th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            `;
            return section;
        }

        function addPoblacionRow(targetId, data = null) {
            const tbody = document.querySelector(`#tabla_poblacion_${targetId} tbody`);
            const rowCount = tbody.children.length + 1;
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${rowCount}</td>
                <td><input type="text" class="form-control form-control-sm" placeholder="Nombre"></td>
                <td><input type="text" class="form-control form-control-sm" placeholder="CI"></td>
                <td><input type="number" class="form-control form-control-sm" placeholder="Edad"></td>
                <td>
                    <select class="form-select form-select-sm">
                        <option>Jefe de hogar</option><option>Cónyuge</option><option>Hijo/a</option>
                        <option>Hermano/a</option><option>Tío/a</option><option>Abuelo/a</option>
                        <option>Sobrino/a</option><option>Ahijado/a</option><option>Cuñado/a</option>
                    </select>
                </td>
                <td><input type="text" class="form-control form-control-sm" placeholder="Grado"></td>
                <td><button class="btn btn-sm btn-danger" onclick="this.closest('tr').remove(); renumberPoblacion('${targetId}')"><i class="fas fa-trash"></i></button></td>
            `;
            if (data) {
                // Rellenar si hay datos (no implementado)
            }
            tbody.appendChild(tr);
            renumberPoblacion(targetId);
        }

        function renumberPoblacion(targetId) {
            const rows = document.querySelectorAll(`#tabla_poblacion_${targetId} tbody tr`);
            rows.forEach((row, idx) => {
                row.children[0].textContent = idx + 1;
            });
        }

        // ========== MODO OCUPANTE ==========
        function createOcupanteBlock() {
            const wrapper = document.createElement('div');
            wrapper.appendChild(createGeographicSection());
            
            const mainCard = document.createElement('div');
            mainCard.className = 'section-card';
            mainCard.innerHTML = `
                <div class="section-header"><i class="fas fa-user me-2"></i>Datos del Ocupante</div>
            `;
            mainCard.appendChild(createPersonFields('ocupante', true));
            mainCard.appendChild(createViviendaConditionSection('ocupante', 'ocupante'));
            mainCard.appendChild(createPoblacionSection('ocupante', 'ocupante'));
            
            // Botón para vivienda adicional
            const extraViv = document.createElement('div');
            extraViv.className = 'p-3 border-top';
            extraViv.innerHTML = `
                <button class="btn btn-outline-secondary btn-sm" onclick="addViviendaAdicional('ocupante')">
                    <i class="fas fa-plus-circle me-1"></i> Agregar vivienda adicional (solo vivienda)
                </button>
                <div id="viviendas_adicionales_ocupante" class="mt-3"></div>
            `;
            mainCard.appendChild(extraViv);
            
            wrapper.appendChild(mainCard);
            return wrapper;
        }

        function addViviendaAdicional(parentId) {
            const container = document.getElementById(`viviendas_adicionales_${parentId}`);
            const count = container.children.length + 1;
            const vivId = `${parentId}_viv${count}`;
            const vivCard = document.createElement('div');
            vivCard.className = 'border p-3 mb-3 bg-light';
            vivCard.id = vivId;
            vivCard.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6 class="mb-0">Vivienda Adicional #${count}</h6>
                    <button class="btn btn-sm btn-danger" onclick="this.closest('.border').remove()"><i class="fas fa-trash"></i></button>
                </div>
                <div class="row mb-2">
                    <div class="col-md-6">
                        <label class="form-label">¿Pariente del ocupante?</label>
                        <select class="form-select">
                            <option>No</option><option>Sí</option>
                        </select>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Parentesco (si aplica)</label>
                        <input type="text" class="form-control">
                    </div>
                </div>
            `;
            // Agregar condición de vivienda para esta vivienda
            vivCard.appendChild(createViviendaConditionSection(vivId, `viv_${count}`));
            // Agregar población para esta vivienda
            vivCard.appendChild(createPoblacionSection(vivId, `viv_${count}`));
            // Botón foto
            const fotoBtn = document.createElement('button');
            fotoBtn.className = 'btn btn-sm btn-outline-primary ms-3';
            fotoBtn.innerHTML = '<i class="fas fa-camera me-1"></i> Agregar foto';
            fotoBtn.onclick = () => openFotosModal(vivId);
            vivCard.querySelector('.vivienda-extra').after(fotoBtn);
            
            container.appendChild(vivCard);
        }

        // ========== MODO CONFLICTO ==========
        function createConflictoBlock() {
            const wrapper = document.createElement('div');
            wrapper.appendChild(createGeographicSection());
            
            const mainCard = document.createElement('div');
            mainCard.className = 'section-card';
            mainCard.innerHTML = `
                <div class="section-header"><i class="fas fa-users me-2"></i>Datos del Lote en Conflicto</div>
            `;
            const pretendientesContainer = document.createElement('div');
            pretendientesContainer.id = 'pretendientes_container';
            pretendientesContainer.className = 'p-3';
            
            // Pretendiente 1 inicial
            pretendientesContainer.appendChild(createPretendienteBlock(1));
            
            mainCard.appendChild(pretendientesContainer);
            
            // Botón agregar pretendiente
            const addBtn = document.createElement('button');
            addBtn.className = 'btn btn-primary m-3';
            addBtn.innerHTML = '<i class="fas fa-plus-circle me-1"></i> Agregar otro pretendiente';
            addBtn.onclick = () => {
                pretendientesCount++;
                pretendientesContainer.appendChild(createPretendienteBlock(pretendientesCount));
            };
            mainCard.appendChild(addBtn);
            
            wrapper.appendChild(mainCard);
            return wrapper;
        }

        function createPretendienteBlock(num) {
            const block = document.createElement('div');
            block.className = 'border p-3 mb-3 bg-white';
            block.id = `pretendiente_${num}`;
            block.innerHTML = `
                <h5 class="text-primary">Pretendiente #${num}</h5>
            `;
            block.appendChild(createPersonFields(`pretendiente_${num}`, true));
            block.appendChild(createViviendaConditionSection(`pretendiente_${num}`, `pret_${num}`));
            block.appendChild(createPoblacionSection(`pretendiente_${num}`, `pret_${num}`));
            // Botón para vivienda adicional para este pretendiente (opcional)
            const extraViv = document.createElement('div');
            extraViv.className = 'p-3 border-top';
            extraViv.innerHTML = `
                <button class="btn btn-outline-secondary btn-sm" onclick="addViviendaAdicional('pretendiente_${num}')">
                    <i class="fas fa-plus-circle me-1"></i> Agregar vivienda adicional
                </button>
                <div id="viviendas_adicionales_pretendiente_${num}" class="mt-3"></div>
            `;
            block.appendChild(extraViv);
            return block;
        }

        // ========== MODO SERVICIO ==========
        function createServicioBlock() {
            const wrapper = document.createElement('div');
            wrapper.appendChild(createGeographicSection());
            const card = document.createElement('div');
            card.className = 'section-card';
            card.innerHTML = `
                <div class="section-header"><i class="fas fa-building me-2"></i>Datos del Servicio</div>
                <div class="p-3">
                    <div class="row g-3">
                        <div class="col-md-4">
                            <label class="form-label">Institución</label>
                            <input type="text" class="form-control" placeholder="Nombre institución">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">RUC Nro.</label>
                            <input type="text" class="form-control" placeholder="RUC">
                        </div>
                        <div class="col-md-4">
                            <label class="form-label">Descripción</label>
                            <input type="text" class="form-control" placeholder="Descripción">
                        </div>
                    </div>
                </div>
            `;
            wrapper.appendChild(card);
            return wrapper;
        }

        // ========== MODO FRACCIONAMIENTO ==========
        function createFraccionamientoBlock() {
            const wrapper = document.createElement('div');
            wrapper.appendChild(createGeographicSection());
            const card = document.createElement('div');
            card.className = 'section-card';
            card.innerHTML = `
                <div class="section-header"><i class="fas fa-cut me-2"></i>Fraccionamiento de Lote</div>
                <div class="p-3">
                    <p>Utilice el botón para generar un sub-lote a partir del lote actual. Cada sub-lote se registrará como un nuevo ocupante.</p>
                    <button class="btn btn-warning" onclick="realizarFraccionamiento()">
                        <i class="fas fa-cut me-1"></i> Realizar fraccionamiento
                    </button>
                    <div id="sublotes_container" class="mt-4"></div>
                </div>
            `;
            wrapper.appendChild(card);
            return wrapper;
        }

        function realizarFraccionamiento() {
            subLotesCount++;
            const container = document.getElementById('sublotes_container');
            const subloteId = `sublote_${subLotesCount}`;
            const letter = String.fromCharCode(64 + subLotesCount); // A, B, C...
            const card = document.createElement('div');
            card.className = 'border p-3 mb-3';
            card.id = subloteId;
            card.innerHTML = `
                <h5 class="text-success">Sub-lote ${letter} (${subloteId})</h5>
            `;
            card.appendChild(createPersonFields(subloteId, true));
            card.appendChild(createViviendaConditionSection(subloteId, `sub_${subLotesCount}`));
            card.appendChild(createPoblacionSection(subloteId, `sub_${subLotesCount}`));
            
            const extraViv = document.createElement('div');
            extraViv.className = 'p-3 border-top';
            extraViv.innerHTML = `
                <button class="btn btn-outline-secondary btn-sm" onclick="addViviendaAdicional('${subloteId}')">
                    <i class="fas fa-plus-circle me-1"></i> Agregar vivienda adicional
                </button>
                <div id="viviendas_adicionales_${subloteId}" class="mt-3"></div>
            `;
            card.appendChild(extraViv);
            container.appendChild(card);
        }

        // ========== FUNCIONES DE MODALES ==========
        function openConyugeModal(btn) {
            currentConyugeTarget = btn.dataset.prefix;
            // Determinar sexo opuesto
            const prefix = btn.dataset.prefix;
            const sexoSelect = document.querySelector(`#${prefix} select`);
            // Buscar el select de sexo más cercano
            const personDiv = btn.closest('.p-3');
            const sexo = personDiv.querySelector('select')?.value;
            const conyugeSexo = document.getElementById('conyugeSexo');
            if (sexo === 'M') conyugeSexo.value = 'F';
            else if (sexo === 'F') conyugeSexo.value = 'M';
            else conyugeSexo.value = 'F';
            new bootstrap.Modal(document.getElementById('modalConyuge')).show();
        }

        function guardarConyuge() {
            // Aquí se guardaría en el estado, por ahora solo cerramos
            bootstrap.Modal.getInstance(document.getElementById('modalConyuge')).hide();
            alert('Datos del cónyuge guardados (simulación)');
        }

        function openCaracteristicasModal(targetId) {
            currentViviendaTarget = targetId;
            new bootstrap.Modal(document.getElementById('modalCaracteristicas')).show();
        }
        function guardarCaracteristicas() {
            bootstrap.Modal.getInstance(document.getElementById('modalCaracteristicas')).hide();
            alert('Características guardadas para ' + currentViviendaTarget);
        }
        function openEquipamientoModal(targetId) {
            currentViviendaTarget = targetId;
            new bootstrap.Modal(document.getElementById('modalEquipamiento')).show();
        }
        function guardarEquipamiento() {
            bootstrap.Modal.getInstance(document.getElementById('modalEquipamiento')).hide();
            alert('Equipamiento guardado para ' + currentViviendaTarget);
        }
        function openResidenciaModal(targetId) {
            currentViviendaTarget = targetId;
            new bootstrap.Modal(document.getElementById('modalResidencia')).show();
        }
        function guardarResidencia() {
            bootstrap.Modal.getInstance(document.getElementById('modalResidencia')).hide();
            alert('Residencia guardada para ' + currentViviendaTarget);
        }
        function openFotosModal(targetId) {
            currentViviendaTarget = targetId;
            document.getElementById('previewFotos').innerHTML = '';
            document.getElementById('inputFotos').value = '';
            new bootstrap.Modal(document.getElementById('modalFotos')).show();
        }
        function guardarFotos() {
            // Simulación: mostrar las fotos seleccionadas como miniaturas
            const input = document.getElementById('inputFotos');
            const preview = document.getElementById('previewFotos');
            if (input.files && input.files.length > 0) {
                Array.from(input.files).forEach(file => {
                    const img = document.createElement('img');
                    img.src = URL.createObjectURL(file);
                    img.className = 'img-thumbnail';
                    preview.appendChild(img);
                });
            }
            bootstrap.Modal.getInstance(document.getElementById('modalFotos')).hide();
            alert(`Fotos guardadas para ${currentViviendaTarget} (${input.files.length} foto(s))`);
        }

        // Inicializar
        document.addEventListener('DOMContentLoaded', () => {
            renderModeContent();
        });
    </script>
</body>
</html>