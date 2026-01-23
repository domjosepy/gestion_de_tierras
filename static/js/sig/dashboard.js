
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar DataTables
    document.querySelectorAll('.beautiful-table').forEach(table => {
        if (table.rows.length > 1) {
            new simpleDatatables.DataTable(table, {
                perPage: 10,
                labels: {
                    placeholder: "Buscar...",
                    perPage: "Registros por página",
                    noRows: "No se encontraron solicitudes",
                    info: "Mostrando {start} a {end} de {rows} solicitudes"
                }
            });
        }
    });
    
    // Modal de asignar usuario
    const modalAsignar = document.getElementById('modalAsignarUsuario');
    if (modalAsignar) {
        modalAsignar.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const solicitudId = button.getAttribute('data-solicitud-id');
            const coloniaNombre = button.getAttribute('data-colonia-nombre');
            
            document.getElementById('solicitudIdAsignar').value = solicitudId;
            document.getElementById('coloniaNombreAsignar').innerHTML = `
                <strong>Solicitud #${solicitudId}</strong><br>
                <small class="text-muted">${coloniaNombre}</small>
            `;
        });
        
        // Formulario de asignación
        document.getElementById('formAsignarUsuario').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const solicitudId = formData.get('solicitud_id');
            const btnSubmit = this.querySelector('button[type="submit"]');
            const originalText = btnSubmit.innerHTML;
            
            btnSubmit.disabled = true;
            btnSubmit.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Asignando...';
            
            try {
                const response = await fetch(`/sig/solicitud/${solicitudId}/asignar-usuario/`, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                    }
                });
                
                const data = await response.json();
                
                if (data.success) {
                    mostrarToast('success', 'Usuario asignado correctamente');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    mostrarToast('error', data.error || 'Error al asignar usuario');
                }
            } catch (error) {
                mostrarToast('error', 'Error de conexión');
            } finally {
                btnSubmit.disabled = false;
                btnSubmit.innerHTML = originalText;
            }
        });
    }
    
    // Funciones auxiliares
    function mostrarToast(tipo, mensaje) {
        // Tu función de toast existente
        console.log(`${tipo}: ${mensaje}`);
    }
});