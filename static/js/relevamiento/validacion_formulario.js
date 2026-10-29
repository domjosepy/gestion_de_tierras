/**
 * Validaciones en tiempo real para formularios de relevamiento
 * Con alertas visuales y prevención de errores comunes
 */

document.addEventListener('DOMContentLoaded', function() {

    // ─────────────────────────────────────────────────────────────
    // VALIDADORES POR CAMPO
    // ─────────────────────────────────────────────────────────────

    const VALIDADORES = {
        manzana: {
            validar: (valor) => {
                if (!valor || valor.trim() === '') {
                    return { valido: false, mensaje: 'El campo manzana no puede estar vacío.' };
                }
                return { valido: true };
            }
        },
        lote_indert: {
            validar: (valor) => {
                if (!valor || valor.trim() === '') {
                    return { valido: false, mensaje: 'El campo lote no puede estar vacío.' };
                }
                return { valido: true };
            }
        },
        quien_es_el_ocupante: {
            validar: (valor) => {
                if (!valor || valor.trim() === '') {
                    return { valido: false, mensaje: 'El nombre del ocupante no puede estar vacío.' };
                }
                const soloLetrasYEnie = /^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s]*$/;
                if (!soloLetrasYEnie.test(valor)) {
                    return { valido: false, mensaje: 'El nombre del ocupante debe contener solo letras y Ñ.' };
                }
                return { valido: true };
            }
        },
        cedula_ocupante: {
            validar: (valor) => {
                if (valor && valor.trim() === '') {
                    return { valido: true };
                }
                if (valor && !/^\d*$/.test(valor)) {
                    return { valido: false, mensaje: 'La cédula debe contener solo números.' };
                }
                if (valor && valor.length > 8) {
                    return { valido: false, mensaje: 'La cédula no debe tener más de 8 dígitos.' };
                }
                return { valido: true };
            }
        },
        quien_es_el_conyuge: {
            validar: (valor) => {
                if (!valor || valor.trim() === '') {
                    return { valido: true };
                }
                const soloLetrasYEnie = /^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s]*$/;
                if (!soloLetrasYEnie.test(valor)) {
                    return { valido: false, mensaje: 'El nombre del cónyuge debe contener solo letras y Ñ.' };
                }
                return { valido: true };
            }
        },
        cedula_conyuge: {
            validar: (valor) => {
                if (!valor || valor.trim() === '') {
                    return { valido: true };
                }
                if (valor && !/^\d*$/.test(valor)) {
                    return { valido: false, mensaje: 'La cédula del cónyuge debe contener solo números.' };
                }
                if (valor && valor.length > 8) {
                    return { valido: false, mensaje: 'La cédula del cónyuge no debe tener más de 8 dígitos.' };
                }
                return { valido: true };
            }
        }
    };

    // ─────────────────────────────────────────────────────────────
    // FUNCIONES UTILITARIAS
    // ─────────────────────────────────────────────────────────────

    function obtenerCampo(nombreCampo) {
        return document.getElementById(`id_${nombreCampo}`);
    }

    function mostrarErrorEnCampo(campo, mensaje) {
        const contenedor = campo.parentElement;
        let errorDiv = contenedor.querySelector('.error-mensaje-inline');

        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'error-mensaje-inline text-danger small mt-1';
            contenedor.appendChild(errorDiv);
        }

        errorDiv.textContent = mensaje;
        errorDiv.style.display = 'block';
        campo.classList.add('is-invalid');
    }

    function limpiarErrorEnCampo(campo) {
        const contenedor = campo.parentElement;
        const errorDiv = contenedor.querySelector('.error-mensaje-inline');

        if (errorDiv) {
            errorDiv.style.display = 'none';
        }

        campo.classList.remove('is-invalid');
    }

    function validarCampo(nombreCampo) {
        const campo = obtenerCampo(nombreCampo);
        if (!campo || !VALIDADORES[nombreCampo]) return true;

        const resultado = VALIDADORES[nombreCampo].validar(campo.value);

        if (resultado.valido) {
            limpiarErrorEnCampo(campo);
        } else {
            mostrarErrorEnCampo(campo, resultado.mensaje);
        }

        return resultado.valido;
    }

    // ─────────────────────────────────────────────────────────────
    // VINCULAR VALIDADORES A CAMPOS
    // ─────────────────────────────────────────────────────────────

    Object.keys(VALIDADORES).forEach(nombreCampo => {
        const campo = obtenerCampo(nombreCampo);
        if (campo) {
            // Validar al perder el foco
            campo.addEventListener('blur', function() {
                validarCampo(nombreCampo);
            });

            // Limpiar errores mientras escribe (si hay un error)
            campo.addEventListener('input', function() {
                if (this.classList.contains('is-invalid')) {
                    validarCampo(nombreCampo);
                }
            });
        }
    });

    // ─────────────────────────────────────────────────────────────
    // VALIDAR AL ENVIAR EL FORMULARIO
    // ─────────────────────────────────────────────────────────────

    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(e) {
            let formularioValido = true;
            const errores = [];

            // Validar cada campo
            Object.keys(VALIDADORES).forEach(nombreCampo => {
                const campo = obtenerCampo(nombreCampo);
                if (campo) {
                    const resultado = VALIDADORES[nombreCampo].validar(campo.value);

                    if (!resultado.valido) {
                        formularioValido = false;
                        mostrarErrorEnCampo(campo, resultado.mensaje);
                        errores.push(resultado.mensaje);
                    } else {
                        limpiarErrorEnCampo(campo);
                    }
                }
            });

            // Si hay errores, mostrar alerta y prevenir envío
            if (!formularioValido) {
                e.preventDefault();
                e.stopPropagation();

                // Scroll al primer error
                const primerErrorCampo = document.querySelector('input.is-invalid, select.is-invalid, textarea.is-invalid');
                if (primerErrorCampo) {
                    primerErrorCampo.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    primerErrorCampo.focus();
                }

                // Mostrar alerta con los errores
                const mensajeErrores = errores.map((err, idx) => `${idx + 1}. ${err}`).join('\n');
                alert('Por favor, corrija los siguientes errores:\n\n' + mensajeErrores);

                return false;
            }
        });
    }

    // ─────────────────────────────────────────────────────────────
    // VALIDACIÓN EN TIEMPO REAL PARA CEDULAS (números únicamente)
    // ─────────────────────────────────────────────────────────────

    ['cedula_ocupante', 'cedula_conyuge'].forEach(nombreCampo => {
        const campo = obtenerCampo(nombreCampo);
        if (campo) {
            campo.addEventListener('input', function() {
                // Remover cualquier carácter que no sea número
                this.value = this.value.replace(/[^\d]/g, '');

                // Limitar a 8 dígitos
                if (this.value.length > 8) {
                    this.value = this.value.slice(0, 8);
                }
            });
        }
    });

    // ─────────────────────────────────────────────────────────────
    // VALIDACIÓN EN TIEMPO REAL PARA NOMBRES (sin números ni símbolos)
    // ─────────────────────────────────────────────────────────────

    ['quien_es_el_ocupante', 'quien_es_el_conyuge'].forEach(nombreCampo => {
        const campo = obtenerCampo(nombreCampo);
        if (campo) {
            campo.addEventListener('input', function() {
                // Permitir solo letras, espacios, acentos y Ñ
                const original = this.value;
                this.value = original.replace(/[^a-zA-ZáéíóúñÁÉÍÓÚÑ\s]/g, '');

                // Si se detectó un cambio, mostrar feedback visual
                if (original !== this.value && original.length > 0) {
                    this.classList.add('is-warning');
                    setTimeout(() => {
                        this.classList.remove('is-warning');
                    }, 1000);
                }
            });
        }
    });

    // ─────────────────────────────────────────────────────────────
    // VALIDACIÓN EN TIEMPO REAL PARA MANZANA Y LOTE
    // ─────────────────────────────────────────────────────────────

    ['manzana', 'lote_indert'].forEach(nombreCampo => {
        const campo = obtenerCampo(nombreCampo);
        if (campo) {
            campo.addEventListener('blur', function() {
                if (this.value.trim() === '') {
                    validarCampo(nombreCampo);
                } else {
                    limpiarErrorEnCampo(this);
                }
            });
        }
    });

    // ─────────────────────────────────────────────────────────────
    // INICIALIZAR: Mostrar errores del servidor si existen
    // ─────────────────────────────────────────────────────────────

    document.querySelectorAll('[class*="errorlist"]').forEach(errorList => {
        const campo = errorList.closest('.col-md-2, .col-md-4, .col-md-6')?.querySelector('input, select, textarea');
        if (campo) {
            campo.classList.add('is-invalid');
        }
    });

});
