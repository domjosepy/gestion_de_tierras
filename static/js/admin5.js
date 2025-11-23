

"use strict";

/**
 * ADMIN5.JS - Sistema de Administración para Bootstrap 5
 * 
 * Módulos principales:
 * - SidebarManager: Gestión del panel lateral
 * - ToastManager: Sistema de notificaciones
 * - FieldValidator: Validación de campos
 * - DataTableManager: Gestión de tablas (Tabulator)
 * - EventManager: Centralización de eventos
 */
document.addEventListener('DOMContentLoaded', function () {
  const toggleButton = document.querySelector('#sidebarToggle');
  const body = document.body;

  if (toggleButton) {
    toggleButton.addEventListener('click', () => {
      body.classList.toggle('sb-sidenav-toggled');

      // Cambiar el ícono si lo deseas
      const icon = toggleButton.querySelector('i');
      if (icon) {
        icon.classList.toggle('fa-angle-double-right');
        icon.classList.toggle('fa-angle-double-left');
      }
    });
  }
});

class SidebarManager {
  static init() {
    if (!document.querySelector('.sidebar')) return;

    this.setupToggleButton();
    this.setupResponsiveBehavior();
    this.restoreState();
    this.setupOutsideClick();
    this.setupAutoExpandOnSubmenuClick();

    /* sirve para inicializar tooltips si se usan en el sidebar
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });*/
  }

  static setupToggleButton() {
    const toggleBtn = document.getElementById('sidebarToggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.toggleSidebar();
        this.saveState();
        this.toggleIcon(toggleBtn);
      });
    }

    const toggleBars = document.getElementById('toggleSidebar');
    if (toggleBars) {
      toggleBars.addEventListener('click', (e) => {
        e.preventDefault();
        this.toggleSidebar();
        this.saveState();
        this.toggleIcon(toggleBars);
      });
    }
  }
  
  static toggleIcon(button) {
    const icon = button.querySelector('i');
    if (icon) {
      icon.classList.toggle('fa-angle-double-left');
      icon.classList.toggle('fa-angle-double-right');
    }
  }

  static setupResponsiveBehavior() {
    const checkViewport = () => {
      const isMobile = window.innerWidth < 768; // Cambiado a 768px

      if (isMobile) {
        // Comportamiento móvil
        document.body.classList.remove('sb-sidenav-toggled');
        document.querySelector('.sidebar')?.classList.remove('active');
        
        // Ocultar submenús
        document.querySelectorAll('.sidebar .collapse').forEach(collapse => {
          collapse.classList.remove('show');
        });
      } else {
        // Comportamiento desktop - restaurar estado guardado
        const savedState = localStorage.getItem('sb|sidebar-toggle');
        if (savedState === 'true') {
          document.body.classList.add('sb-sidenav-toggled');
        } else {
          document.body.classList.remove('sb-sidenav-toggled');
        }
      }
    };

    // Ejecutar al cargar y en cambios de tamaño
    checkViewport();
    window.addEventListener('resize', checkViewport);
  }

  /**
   * Alterna el estado del sidebar entre colapsado y expandido
   */
  static toggleSidebar() {
    
    const isMobile = window.innerWidth < 768;
    const sidebar = document.querySelector('.sidebar');

    if (isMobile) {
        // Comportamiento móvil - toggle de visibilidad completa
        sidebar?.classList.toggle('active');
      } else {
        // Comportamiento desktop - toggle de estado colapsado
        document.body.classList.toggle('sb-sidenav-toggled');
        this.saveState();
        
        // Actualizar el ancho del sidebar
        const rootStyles = getComputedStyle(document.documentElement);
        const collapsedWidth = rootStyles.getPropertyValue('--sidebar-collapsed-width').trim();
        const expandedWidth = rootStyles.getPropertyValue('--sidebar-width').trim();
        
        if (sidebar) {
          const isCollapsed = document.body.classList.contains('sb-sidenav-toggled');
          sidebar.style.width = isCollapsed ? collapsedWidth : expandedWidth;
        }
    }
     // Actualizar el icono del botón
    const toggleBtn = document.getElementById('sidebarToggle');
    if (toggleBtn) this.toggleIcon(toggleBtn);
  }


  static setupOutsideClick() {
    document.querySelectorAll('.sidebar .nav-item').forEach(item => {
      const collapse = item.querySelector('.collapse');
      if (!collapse) return;

      item.addEventListener('mouseenter', () => {
        if (document.body.classList.contains('sb-sidenav-toggled')) return;
        collapse.classList.add('show');
      });

      item.addEventListener('mouseleave', () => {
        collapse.classList.remove('show');
      });
    });
  }

  static setupAutoExpandOnSubmenuClick() {
    document.querySelectorAll('.sidebar .nav-item .nav-link').forEach(link => {
      link.addEventListener('click', () => {
        if (document.body.classList.contains('sb-sidenav-toggled')) {
          document.body.classList.remove('sb-sidenav-toggled');
          this.saveState();

          const sidebar = document.querySelector('.sidebar');
          if (sidebar) {
            const rootStyles = getComputedStyle(document.documentElement);
            const expandedWidth = rootStyles.getPropertyValue('--sidebar-width').trim();
            sidebar.style.width = expandedWidth;
          }
        }
      });
    });
  }

  static saveState() {
    localStorage.setItem('sb|sidebar-toggle', document.body.classList.contains('sb-sidenav-toggled'));
  }

  static restoreState() {
    const savedState = localStorage.getItem('sb|sidebar-toggle');
    const toggleBtn = document.getElementById('sidebarToggle');
    const toggleBars = document.getElementById('toggleSidebar');

    if (savedState === 'true') {
      document.body.classList.add('sb-sidenav-toggled');
      if (toggleBtn) this.toggleIcon(toggleBtn);
      if (toggleBars) this.toggleIcon(toggleBars);
    } else {
      document.body.classList.remove('sb-sidenav-toggled');
      if (toggleBtn) this.toggleIcon(toggleBtn);
      if (toggleBars) this.toggleIcon(toggleBars);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => SidebarManager.init());



class ToastManager {
  // Mapeo de iconos para cada tipo de toast
  static icons = {
    success: 'fa-check-circle',
    error: 'fa-exclamation-circle',
    danger: 'fa-exclamation-circle',
    warning: 'fa-exclamation-triangle',
    info: 'fa-info-circle'
  };
  
  /**
   * Inicializa todos los toasts existentes en el DOM
   */
  static initialize() {
    document.querySelectorAll('.toast').forEach(toastEl => {
      this.showToast(toastEl);
    });
  }

  /**
   * Crea y muestra un nuevo toast
   * @param {string} message - Mensaje a mostrar
   * @param {string} type - Tipo de toast (success, error, warning, info)
   * @param {object} options - Opciones adicionales (delay)
   */
  static create(message, type = 'info', options = {}) {
    const toastContainer = document.querySelector('.toast-container') || document.body;
    const toastEl = document.createElement('div');
    
    // Configuración básica del toast
    toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    const delay = options.delay || 5000;
    toastEl.dataset.bsDelay = delay.toString();

    // Estructura HTML del toast
    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">
          <i class="fas ${this.icons[type]} me-2"></i> ${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-3 m-auto" 
                data-bs-dismiss="toast" aria-label="Close"></button>
      </div>`;

    toastContainer.appendChild(toastEl);
    this.showToast(toastEl);
  }

  /**
   * Muestra un toast y configura su autodestrucción
   * @param {HTMLElement} toastEl - Elemento DOM del toast
   */
  static showToast(toastEl) {
    const toast = new bootstrap.Toast(toastEl, {
      autohide: true,
      delay: parseInt(toastEl.dataset.bsDelay) || 5000
    });
    
    toast.show();
    
    // Elimina el toast del DOM cuando se oculta
    toastEl.addEventListener('hidden.bs.toast', () => {
      toastEl.remove();
    });
  }
}

/**

 * Funcionalidades principales:
 * - Validación de formulario
 * - Toggle de visibilidad de contraseña
 * - Manejo de mensajes de error
 * - Integración con Django Messages
 */

class LoginManager {
  static init() {
    this.form = document.querySelector('.needs-validation');
    this.passwordInput = document.getElementById('password');
    this.toggleBtn = document.querySelector('.toggle-password');

    this.setupPasswordToggle();
    this.setupFormValidation();
    this.setupErrorEffects();
    this.autoCloseAlerts();
    this.setupInputAnimations();
  }

  // Configuración del toggle de contraseña mejorado
  static setupPasswordToggle() {
    if (this.toggleBtn && this.passwordInput) {
      const icon = this.toggleBtn.querySelector('i');
      
      this.toggleBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const isPassword = this.passwordInput.type === 'password';
        this.passwordInput.type = isPassword ? 'text' : 'password';
        //icon.classList.toggle('fa-eye-slash');
        //icon.classList.toggle('fa-eye'); 
        
        // Feedback táctil
        this.toggleBtn.classList.add('active');
        setTimeout(() => this.toggleBtn.classList.remove('active'), 200);
      });
    }
  }



  // Validación de formulario mejorada
 static setupFormValidation() {
    if (!this.form) return;

    this.form.addEventListener('submit', (e) => {
      e.preventDefault();
      let isValid = true;

      const requiredFields = this.form.querySelectorAll('[required]');
      requiredFields.forEach(field => {
        const icon = document.getElementById(`${field.id}-icon`);
        field.classList.remove('is-invalid');

        if (!field.value.trim()) {
          field.classList.add('is-invalid');
          isValid = false;

          // Mostrar ícono
          if (icon) {
            icon.classList.add('show');
            setTimeout(() => icon.classList.remove('show'), 3000);
          }

          // Shake
          field.style.animation = 'shake 0.5s';
          setTimeout(() => field.style.animation = '', 500);
        }
      });

      if (!isValid) {
        this.form.classList.add('was-validated');
        this.showToast('Por favor complete todos los campos requeridos', 'danger');
        return;
      }

      const submitBtn = this.form.querySelector('button[type="submit"]');
      if (submitBtn) {
        const spinner = submitBtn.querySelector('.spinner-border');
        const text = submitBtn.querySelector('.submit-text');
        submitBtn.disabled = true;
        spinner?.classList.remove('d-none');
        if (text) text.textContent = 'Verificando...';
      }

      setTimeout(() => this.form.submit(), 500);
    });

    this.form.querySelectorAll('input').forEach(input => {
      input.addEventListener('input', () => {
        input.classList.remove('is-invalid');
      });
    });
  }


  // Efectos para errores del backend
  static setupErrorEffects() {
    const errorAlert = document.querySelector('.alert-danger');
    if (!errorAlert) return;

    ['username', 'password'].forEach(id => {
      const field = document.getElementById(id);
      if (field) {
        field.classList.add('is-invalid');
        
        // Remover el error al enfocar
        field.addEventListener('focus', () => {
          field.classList.remove('is-invalid');
        }, { once: true });
      }
    });
  }

  // Cierre automático de alertas
  static autoCloseAlerts() {
    document.querySelectorAll('.alert').forEach(alert => {
      setTimeout(() => {
        bootstrap.Alert.getOrCreateInstance(alert).close();
      }, 5000);
    });
  }

  // Animaciones para inputs
  static setupInputAnimations() {
    const inputs = document.querySelectorAll('.form-control');
    inputs.forEach(input => {
      input.addEventListener('focus', () => {
        input.parentElement.classList.add('focused');
      });
      
      input.addEventListener('blur', () => {
        input.parentElement.classList.remove('focused');
      });
    });
  }

  // Mostrar toast notifications
  static showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container') || document.body;
    const toastId = `toast-${Date.now()}`;
    
    const toastEl = document.createElement('div');
    toastEl.id = toastId;
    toastEl.className = `toast show align-items-center text-white bg-${type} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center">
          <i class="fas ${this.getToastIcon(type)} me-3 fs-5"></i>
          <span>${message}</span>
        </div>
        <button type="button" class="btn-close btn-close-white me-3 m-auto" 
          data-bs-dismiss="toast" aria-label="Close"></button>
      </div>`;

    toastContainer.appendChild(toastEl);
    
    // Configurar auto-cierre
    setTimeout(() => {
      const toastInstance = bootstrap.Toast.getOrCreateInstance(toastEl);
      toastInstance.hide();
      
      toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
      });
    }, 5000);
  }

  // Obtener icono según tipo de toast
  static getToastIcon(type) {
    const icons = {
      success: 'fa-check-circle',
      error: 'fa-exclamation-circle',
      danger: 'fa-exclamation-circle',
      warning: 'fa-exclamation-triangle',
      info: 'fa-info-circle'
    };
    return icons[type] || icons.info;
  }
}


class FieldValidator {
  /**
   * Inicializa la validación de campos
   */
  static init() {
    this.setupNumericField('id_ci', 8, 'La cédula debe tener 8 dígitos');
    this.setupNumericField('id_telefono', 10, 'El teléfono debe tener 10 dígitos');
  }

  /**
   * Configura validación para campos numéricos
   * @param {string} fieldId - ID del campo a validar
   * @param {number} maxLength - Longitud máxima permitida
   * @param {string} errorMessage - Mensaje de error a mostrar
   */
  static setupNumericField(fieldId, maxLength, errorMessage) {
    const field = document.getElementById(fieldId);
    if (!field) return;

    field.addEventListener('input', () => {
      // Solo permite números
      field.value = field.value.replace(/[^0-9]/g, '');
      
      // Limita la longitud máxima
      if (field.value.length > maxLength) {
        field.value = field.value.slice(0, maxLength);
      }

      // Muestra error si no tiene la longitud exacta
      if (field.value.length > 0 && field.value.length !== maxLength) {
        this.showError(fieldId, errorMessage);
      } else {
        this.clearError(fieldId);
      }
    });
  }

  /**
   * Muestra un mensaje de error para un campo
   */
  static showError(fieldId, message) {
    const field = document.getElementById(fieldId);
    if (!field) return;

    let errorDiv = field.nextElementSibling;
    if (!errorDiv || !errorDiv.classList.contains('invalid-feedback')) {
      errorDiv = document.createElement('div');
      errorDiv.className = 'invalid-feedback';
      field.classList.add('is-invalid');
      field.parentNode.insertBefore(errorDiv, field.nextSibling);
    }

    errorDiv.innerHTML = `<i class="fas fa-exclamation-circle me-1"></i> ${message}`;
  }

  /**
   * Limpia el mensaje de error de un campo
   */
  static clearError(fieldId) {
    const field = document.getElementById(fieldId);
    if (!field) return;

    const errorDiv = field.nextElementSibling;
    if (errorDiv && errorDiv.classList.contains('invalid-feedback')) {
      field.classList.remove('is-invalid');
      errorDiv.remove();
    }
  }
}

class ScrollManager {
  /**
   * Inicializa las funcionalidades de scroll
   */
  static init() {
    this.setupScrollToTop();
  }

  /**
   * Configura el botón de scroll to top
   * - Muestra/oculta el botón según la posición del scroll
   * - Maneja el click para hacer scroll suave al inicio
   */
  static setupScrollToTop() {
    const btn = document.querySelector('.scroll-to-top');
    if (!btn) return;

    window.addEventListener('scroll', () => {
      btn.classList.toggle('show', window.scrollY > 100);
    });

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });
  }
}

class DataTableManager {
  /**
   * Inicializa las tablas con Tabulator
   */
  static init() {
    if (typeof Tabulator === 'undefined') return;
    
    this.tables = [];
    document.querySelectorAll('[data-tabulator]').forEach(el => {
      this.tables.push(this.createTable(el));
    });
  }

  /**
   * Crea una nueva instancia de Tabulator
   * @param {HTMLElement} element - Elemento contenedor de la tabla
   * @returns {Tabulator} - Instancia de Tabulator
   */
  static createTable(element) {
    return new Tabulator(element, {
      layout: "fitColumns",
      responsiveLayout: "collapse",
      pagination: true,
      paginationSize: 10,
      paginationSizeSelector: [5, 10, 20, 50],
      movableColumns: true,
      resizableRows: true,
      ajaxURL: element.dataset.url,
      ajaxParams: JSON.parse(element.dataset.params || '{}'),
      columns: JSON.parse(element.dataset.columns || '[]')
    });
  }
}



// Inicialización principal cuando el DOM está listo
document.addEventListener('DOMContentLoaded', () => {
  // Inicializar todos los módulos
  LoginManager.init();
  SidebarManager.init();
  ToastManager.initialize();
  FieldValidator.init();
  ScrollManager.init();
  DataTableManager.init();

 
   
  // Mostrar submenús solo al pasar el mouse
  document.querySelectorAll('.sidebar .nav-item').forEach(item => {
    const collapse = item.querySelector('.collapse');
    if (!collapse) return;

    item.addEventListener('mouseenter', () => {
      if (document.body.classList.contains('sb-sidenav-toggled')) return;
      collapse.classList.add('show');
    });

    item.addEventListener('mouseleave', () => {
      collapse.classList.remove('show');
    });
  });
});

function soloTexto(input) {
  // Permite solo letras (mayúsculas y minúsculas) y espacios
  input.value = input.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s']/g, '');
}
// Hacer ToastManager disponible globalmente
window.ToastManager = ToastManager;