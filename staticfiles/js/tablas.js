// static/js/table.js

// Prevenir auto-inicialización de Simple-DataTables
if (window.simpleDatatables) {
    // Desactivar el auto-inicio si existe
    window.simpleDatatables.DataTable.autoInit = false;
}
function initTables() {
    if (!window.simpleDatatables) {
        console.warn("⚠️ simple-datatables no está disponible.");
        return;
    }

     // Destruir instancias anteriores para evitar duplicados
    if (window.dataTableInstances) {
        window.dataTableInstances.forEach(instance => {
            if (instance && instance.destroy) {
                try {
                    instance.destroy();
                } catch (e) {
                    console.warn('Error destruyendo DataTable:', e);
                }
            }
        });
        window.dataTableInstances = [];
    }
    // Inicializar tablas que aún no han sido inicializadas
    document.querySelectorAll("table[id^='tablaUsuarios-']").forEach(tabla => {
        // Solo inicializar tablas visibles (en pestañas activas)
        const isVisible = tabla.closest('.tab-pane')?.classList.contains('active') || 
                         tabla.closest('.modal')?.classList.contains('show');
        
        if (!isVisible) return;
        if (tabla.hasAttribute("data-initialized")) return;

        try {
            const tablaId = tabla.id.replace("tablaUsuarios-", "");
            const datatable = new simpleDatatables.DataTable(tabla, {
                perPage: 10,
                labels: {
                    placeholder: "Buscar...",
                    perPage: "Registros por página",
                    noRows: "No se encontraron registros",
                    info: "Mostrando {start} a {end} de {rows} registros"
                }
            });

            datatable.on('datatable.render', function() {
                reinicializarDropdowns(tablaId);
            });

            tabla.setAttribute("data-initialized", "true");
            window.dataTableInstances = window.dataTableInstances || [];
            window.dataTableInstances.push(datatable);
            
            console.log(`✅ Tabla inicializada: ${tablaId}`);
        } catch (error) {
            console.error(`❌ Error inicializando tabla:`, error);
        }
    });
}


// Función para reinicializar dropdowns
function reinicializarDropdowns(tablaId) {
    const tabla = document.getElementById(`tablaUsuarios-${tablaId}`);
    if (!tabla) return;
    
    tabla.querySelectorAll('.dropdown-toggle').forEach(toggle => {
        // Destruir instancia previa si existe
        const dropdown = bootstrap.Dropdown.getInstance(toggle);
        if (dropdown) dropdown.dispose();
        
        // Crear nueva instancia
        new bootstrap.Dropdown(toggle);
    });
    
    console.log(`🔄 Dropdowns reinicializados para tabla: ${tablaId}`);
}

// Inicializar al cargar la página
document.addEventListener("DOMContentLoaded", initTables);

// Reinicializar al cambiar de pestaña (Bootstrap tabs)
document.addEventListener("shown.bs.tab", function(e) {
    initTables();
    
    // También reinicializar dropdowns de la pestaña activa
    const activePane = document.querySelector('.tab-pane.active');
    if (activePane) {
        activePane.querySelectorAll('.dropdown-toggle').forEach(toggle => {
            const dropdown = bootstrap.Dropdown.getInstance(toggle);
            if (dropdown) dropdown.dispose();
            new bootstrap.Dropdown(toggle);
        });
    }
});