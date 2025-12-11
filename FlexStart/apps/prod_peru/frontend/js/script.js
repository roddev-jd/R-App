// Configuración de API base
const API_BASE = '/prod_peru';

// Estado global de la aplicación
let currentUser = null;
let isAuthenticated = false;
let authToken = null;

// Constantes para localStorage
const TOKEN_KEY = 'prod_peru_auth_token';
const USER_KEY = 'prod_peru_auth_user';

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    // Verificar si hay parámetros de autenticación en la URL (callback de Microsoft)
    const urlParams = new URLSearchParams(window.location.search);
    const authTokenParam = urlParams.get('auth_token');
    const authUserParam = urlParams.get('auth_user');
    const authError = urlParams.get('auth_error');

    // Limpiar URL de parámetros de autenticación
    if (authTokenParam || authUserParam || authError) {
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    // Manejar error de autenticación
    if (authError) {
        showAuthError(decodeURIComponent(authError));
        showAuthModal();
        return;
    }

    // Si hay token en URL (callback exitoso), guardarlo
    if (authTokenParam && authUserParam) {
        localStorage.setItem(TOKEN_KEY, authTokenParam);
        localStorage.setItem(USER_KEY, authUserParam);
    }

    // Verificar si hay token guardado
    const savedToken = localStorage.getItem(TOKEN_KEY);
    const savedUser = localStorage.getItem(USER_KEY);

    if (savedToken && savedUser) {
        // Intentar restaurar sesión
        authToken = savedToken;
        const restored = await restoreSession();
        if (restored) {
            return; // Sesión restaurada exitosamente
        }
    }

    // Mostrar modal de autenticación
    showAuthModal();
}

async function showAuthModal() {
    const authModal = new bootstrap.Modal(document.getElementById('authModal'));
    authModal.show();

    // Event listeners
    setupEventListeners();
}

async function restoreSession() {
    try {
        const response = await fetch(`${API_BASE}/api/auth/me`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success && data.user) {
                currentUser = data.user;
                isAuthenticated = true;
                showMainContent();
                setupEventListeners();
                return true;
            }
        }

        // Token inválido o expirado
        clearAuthData();
        return false;

    } catch (error) {
        console.error('Error restaurando sesión:', error);
        clearAuthData();
        return false;
    }
}

function clearAuthData() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    authToken = null;
    currentUser = null;
    isAuthenticated = false;
}


function setupEventListeners() {
    // Autenticación - solo si el botón existe (modal visible)
    const authBtn = document.getElementById('auth-btn');
    if (authBtn) {
        // Remover listeners previos
        authBtn.replaceWith(authBtn.cloneNode(true));
        document.getElementById('auth-btn').addEventListener('click', handleAuthentication);
    }

    // Logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.replaceWith(logoutBtn.cloneNode(true));
        document.getElementById('logout-btn').addEventListener('click', handleLogout);
    }

    // Declaraciones
    const declBtn = document.getElementById('load-declaration-button');
    if (declBtn) {
        declBtn.replaceWith(declBtn.cloneNode(true));
        document.getElementById('load-declaration-button').addEventListener('click', handleDeclaration);
    }

    const declText = document.getElementById('declaration-text');
    if (declText) {
        declText.addEventListener('input', validateDeclarationForm);
    }

    // Rechazos
    const rejBtn = document.getElementById('load-rejection-button');
    if (rejBtn) {
        rejBtn.replaceWith(rejBtn.cloneNode(true));
        document.getElementById('load-rejection-button').addEventListener('click', handleRejection);
    }

    const rejText = document.getElementById('rejection-text');
    const rejObs = document.getElementById('rejection-obs-text');
    if (rejText) rejText.addEventListener('input', validateRejectionForm);
    if (rejObs) rejObs.addEventListener('input', validateRejectionForm);

    // Diseño Pendiente Chile
    const pendingDesignButton = document.getElementById('load-pending-design-button');
    const pendingDesignText = document.getElementById('pending-design-text');
    if (pendingDesignButton && pendingDesignText) {
        pendingDesignButton.replaceWith(pendingDesignButton.cloneNode(true));
        document.getElementById('load-pending-design-button').addEventListener('click', handlePendingDesign);
        pendingDesignText.addEventListener('input', validatePendingDesignForm);
    }

    // Diseño Pendiente Peru
    const pendingDesignPeruButton = document.getElementById('load-pending-design-peru-button');
    const pendingDesignPeruText = document.getElementById('pending-design-peru-text');
    if (pendingDesignPeruButton && pendingDesignPeruText) {
        pendingDesignPeruButton.replaceWith(pendingDesignPeruButton.cloneNode(true));
        document.getElementById('load-pending-design-peru-button').addEventListener('click', handlePendingDesignPeru);
        pendingDesignPeruText.addEventListener('input', validatePendingDesignPeruForm);
    }

    // Collapse icons
    setupCollapseIcons();
}

function handleAuthentication() {
    // Mostrar loading
    const authBtn = document.getElementById('auth-btn');
    authBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Redirigiendo a Microsoft...';
    authBtn.disabled = true;

    // Redirigir a Microsoft para autenticación directa
    window.location.href = `${API_BASE}/api/auth/login`;
}

function showMainContent() {
    // Ocultar modal si está abierto
    const authModalEl = document.getElementById('authModal');
    const authModal = bootstrap.Modal.getInstance(authModalEl);
    if (authModal) {
        authModal.hide();
    }

    // Usar display_name para la navegación y real_name para la bienvenida con género
    document.getElementById('current-user').textContent = currentUser.display_name;

    // Determinar saludo según el género
    const greeting = currentUser.gender === 'female' ? 'Bienvenida' : 'Bienvenido';
    const realName = currentUser.real_name || currentUser.display_name;
    document.getElementById('current-user-hero').textContent = `${greeting}, ${realName}`;

    // Mostrar columna de diseño pendiente si el usuario tiene acceso
    if (currentUser.has_pending_design_access) {
        const pendingDesignColumn = document.getElementById('pending-design-column');
        if (pendingDesignColumn) {
            pendingDesignColumn.style.display = 'block';
        }
    }

    document.getElementById('main-content').style.display = 'block';
    document.getElementById('main-content').classList.add('fade-in');
}

async function handleLogout() {
    try {
        // Llamar endpoint de logout (opcional, para logging)
        if (authToken) {
            await fetch(`${API_BASE}/api/auth/logout`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`,
                    'Content-Type': 'application/json'
                }
            });
        }
    } catch (error) {
        console.error('Error en logout:', error);
    }

    // Limpiar estado
    clearAuthData();

    // Limpiar formularios
    document.getElementById('declaration-text').value = '';
    document.getElementById('rejection-text').value = '';
    document.getElementById('rejection-obs-text').value = '';

    // Limpiar y ocultar diseño pendiente Chile
    const pendingDesignText = document.getElementById('pending-design-text');
    const pendingDesignColumn = document.getElementById('pending-design-column');
    if (pendingDesignText) {
        pendingDesignText.value = '';
    }
    if (pendingDesignColumn) {
        pendingDesignColumn.style.display = 'none';
    }

    // Limpiar diseño pendiente Peru
    const pendingDesignPeruText = document.getElementById('pending-design-peru-text');
    if (pendingDesignPeruText) {
        pendingDesignPeruText.value = '';
    }

    // Ocultar contenido principal y mostrar modal de auth
    document.getElementById('main-content').style.display = 'none';

    // Recargar la página para mostrar el modal limpio
    window.location.reload();
}

// Helper para hacer requests autenticados
async function authenticatedFetch(url, options = {}) {
    if (!authToken) {
        throw new Error('No hay token de autenticación');
    }

    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
    };

    const response = await fetch(url, {
        ...options,
        headers
    });

    // Si el token expiró, redirigir a login
    if (response.status === 401) {
        clearAuthData();
        showAuthError('Tu sesión ha expirado. Por favor, inicia sesión nuevamente.');
        document.getElementById('main-content').style.display = 'none';
        showAuthModal();
        throw new Error('Sesión expirada');
    }

    return response;
}

async function handleDeclaration() {
    if (!isAuthenticated || !currentUser) {
        showError('declaration-status', 'No estás autenticado');
        return;
    }

    const declarationText = document.getElementById('declaration-text').value.trim();

    if (!declarationText) {
        showError('declaration-status', 'Por favor, escribe la información a declarar');
        return;
    }

    // Mostrar loading overlay
    showLoading('Procesando Declaración', 'Enviando información al servidor...');

    try {
        // Simular progreso
        setTimeout(() => {
            updateLoadingMessage('Procesando columnas automáticamente...');
        }, 1000);

        setTimeout(() => {
            updateLoadingMessage('Cargando datos a SharePoint...');
        }, 2000);

        const response = await authenticatedFetch(`${API_BASE}/api/load-declaration`, {
            method: 'POST',
            body: JSON.stringify({
                team_member: currentUser.member_id,
                declaration_text: declarationText
            })
        });

        const data = await response.json();

        // Ocultar loading
        hideLoading();

        if (response.ok && data.success) {
            showSuccess('declaration-status', data.message || 'Declaración cargada exitosamente');
            document.getElementById('declaration-text').value = '';
        } else {
            showError('declaration-status', data.message || data.detail || 'Error al cargar la declaración');
        }
    } catch (error) {
        // Ocultar loading en caso de error
        hideLoading();
        if (error.message !== 'Sesión expirada') {
            console.error('Error en declaración:', error);
            showError('declaration-status', 'Error de conexión. Intenta nuevamente.');
        }
    }
}

async function handleRejection() {
    if (!isAuthenticated || !currentUser) {
        showError('rejection-status', 'No estás autenticado');
        return;
    }

    const rejectionText = document.getElementById('rejection-text').value.trim();
    const rejectionObs = document.getElementById('rejection-obs-text').value.trim();

    if (!rejectionText) {
        showError('rejection-status', 'Por favor, escribe la información del rechazo');
        return;
    }

    if (!rejectionObs) {
        showError('rejection-status', 'Por favor, escribe la observación del rechazo');
        return;
    }

    // Mostrar loading overlay
    showLoading('Procesando Rechazo', 'Enviando información al servidor...');

    try {
        // Simular progreso
        setTimeout(() => {
            updateLoadingMessage('Procesando columnas automáticamente...');
        }, 1000);

        setTimeout(() => {
            updateLoadingMessage('Cargando datos de rechazo a SharePoint...');
        }, 2000);

        const response = await authenticatedFetch(`${API_BASE}/api/load-rejection`, {
            method: 'POST',
            body: JSON.stringify({
                team_member: currentUser.member_id,
                rejection_text: rejectionText,
                rejection_obs: rejectionObs
            })
        });

        const data = await response.json();

        // Ocultar loading
        hideLoading();

        if (response.ok && data.success) {
            showSuccess('rejection-status', data.message || 'Rechazo cargado exitosamente');
            document.getElementById('rejection-text').value = '';
            document.getElementById('rejection-obs-text').value = '';
        } else {
            showError('rejection-status', data.message || data.detail || 'Error al cargar el rechazo');
        }
    } catch (error) {
        // Ocultar loading en caso de error
        hideLoading();
        if (error.message !== 'Sesión expirada') {
            console.error('Error en rechazo:', error);
            showError('rejection-status', 'Error de conexión. Intenta nuevamente.');
        }
    }
}

function validateDeclarationForm() {
    const declarationText = document.getElementById('declaration-text').value.trim();
    const button = document.getElementById('load-declaration-button');
    button.disabled = !declarationText;
}

function validateRejectionForm() {
    const rejectionText = document.getElementById('rejection-text').value.trim();
    const rejectionObs = document.getElementById('rejection-obs-text').value.trim();
    const button = document.getElementById('load-rejection-button');
    button.disabled = !rejectionText || !rejectionObs;
}

async function handlePendingDesign() {
    if (!isAuthenticated || !currentUser) {
        showError('pending-design-status', 'No estás autenticado');
        return;
    }

    // Verificar si el usuario tiene acceso a diseño pendiente
    if (!currentUser.has_pending_design_access) {
        showError('pending-design-status', 'No tienes acceso a esta funcionalidad');
        return;
    }

    const pendingDesignText = document.getElementById('pending-design-text').value.trim();

    if (!pendingDesignText) {
        showError('pending-design-status', 'Por favor, escribe la información del diseño pendiente');
        return;
    }

    // Mostrar loading overlay
    showLoading('Procesando Diseño Pendiente', 'Enviando información al servidor...');

    try {
        // Simular progreso
        setTimeout(() => {
            updateLoadingMessage('Procesando datos automáticamente...');
        }, 1000);

        setTimeout(() => {
            updateLoadingMessage('Cargando diseño pendiente a S3...');
        }, 2000);

        const response = await authenticatedFetch(`${API_BASE}/api/load-pending-design`, {
            method: 'POST',
            body: JSON.stringify({
                team_member: currentUser.member_id,
                pending_design_text: pendingDesignText
            })
        });

        const data = await response.json();

        // Ocultar loading
        hideLoading();

        if (response.ok && data.success) {
            showSuccess('pending-design-status', data.message || 'Diseño pendiente cargado exitosamente');
            document.getElementById('pending-design-text').value = '';
        } else {
            showError('pending-design-status', data.message || data.detail || 'Error al cargar el diseño pendiente');
        }
    } catch (error) {
        // Ocultar loading en caso de error
        hideLoading();
        if (error.message !== 'Sesión expirada') {
            console.error('Error en diseño pendiente:', error);
            showError('pending-design-status', 'Error de conexión. Intenta nuevamente.');
        }
    }
}

function validatePendingDesignForm() {
    const pendingDesignText = document.getElementById('pending-design-text').value.trim();
    const button = document.getElementById('load-pending-design-button');
    if (button) {
        button.disabled = !pendingDesignText;
    }
}

async function handlePendingDesignPeru() {
    if (!isAuthenticated || !currentUser) {
        showError('pending-design-peru-status', 'No estás autenticado');
        return;
    }

    // Verificar si el usuario tiene acceso a diseño pendiente
    if (!currentUser.has_pending_design_access) {
        showError('pending-design-peru-status', 'No tienes acceso a esta funcionalidad');
        return;
    }

    const pendingDesignPeruText = document.getElementById('pending-design-peru-text').value.trim();

    if (!pendingDesignPeruText) {
        showError('pending-design-peru-status', 'Por favor, escribe la información del diseño pendiente para PERU');
        return;
    }

    // Mostrar loading overlay
    showLoading('Procesando Diseño Pendiente PERU', 'Enviando información al servidor...');

    try {
        // Simular progreso
        setTimeout(() => {
            updateLoadingMessage('Procesando datos automáticamente...');
        }, 1000);

        setTimeout(() => {
            updateLoadingMessage('Cargando diseño pendiente PERU a S3...');
        }, 2000);

        const response = await authenticatedFetch(`${API_BASE}/api/load-pending-design-peru`, {
            method: 'POST',
            body: JSON.stringify({
                team_member: currentUser.member_id,
                pending_design_text: pendingDesignPeruText
            })
        });

        const data = await response.json();

        // Ocultar loading
        hideLoading();

        if (response.ok && data.success) {
            showSuccess('pending-design-peru-status', data.message || 'Diseño pendiente PERU cargado exitosamente');
            document.getElementById('pending-design-peru-text').value = '';
        } else {
            showError('pending-design-peru-status', data.message || data.detail || 'Error al cargar el diseño pendiente PERU');
        }
    } catch (error) {
        // Ocultar loading en caso de error
        hideLoading();
        if (error.message !== 'Sesión expirada') {
            console.error('Error en diseño pendiente PERU:', error);
            showError('pending-design-peru-status', 'Error de conexión. Intenta nuevamente.');
        }
    }
}

function validatePendingDesignPeruForm() {
    const pendingDesignPeruText = document.getElementById('pending-design-peru-text').value.trim();
    const button = document.getElementById('load-pending-design-peru-button');
    if (button) {
        button.disabled = !pendingDesignPeruText;
    }
}

function setupCollapseIcons() {
    // Configurar iconos de collapse
    const collapseElements = document.querySelectorAll('[data-bs-toggle="collapse"]');

    collapseElements.forEach(element => {
        const targetId = element.getAttribute('data-bs-target');
        const targetElement = document.querySelector(targetId);

        if (targetElement) {
            targetElement.addEventListener('show.bs.collapse', () => {
                const icon = element.querySelector('.bi-chevron-right, .bi-chevron-down');
                if (icon) {
                    icon.classList.remove('bi-chevron-right');
                    icon.classList.add('bi-chevron-down');
                }
            });

            targetElement.addEventListener('hide.bs.collapse', () => {
                const icon = element.querySelector('.bi-chevron-right, .bi-chevron-down');
                if (icon) {
                    icon.classList.remove('bi-chevron-down');
                    icon.classList.add('bi-chevron-right');
                }
            });
        }
    });
}

// Utilidades de Loading
function showLoading(title = 'Procesando...', message = 'Por favor espera mientras procesamos tu solicitud') {
    const overlay = document.getElementById('loading-overlay');
    const titleElement = document.querySelector('.loading-title');
    const messageElement = document.getElementById('loading-message');

    titleElement.textContent = title;
    messageElement.textContent = message;
    overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    overlay.style.display = 'none';
}

function updateLoadingMessage(message) {
    const messageElement = document.getElementById('loading-message');
    messageElement.textContent = message;
}

// Utilidades de UI
function showAuthError(message) {
    const errorDiv = document.getElementById('auth-error');
    const errorMessage = document.getElementById('auth-error-message');
    errorMessage.textContent = message;
    errorDiv.classList.remove('d-none');
}

function hideAuthError() {
    document.getElementById('auth-error').classList.add('d-none');
}

/**
 * Show notification modal with success or error styling
 * @param {string} type - 'success' or 'error'
 * @param {string} message - Message to display
 */
function showNotificationModal(type, message) {
    const modal = document.getElementById('notificationModal');
    const header = document.getElementById('notificationModalHeader');
    const titleText = document.getElementById('notificationModalTitleText');
    const headerIcon = document.getElementById('notificationModalIcon');
    const bodyIcon = document.getElementById('notificationModalBodyIcon');
    const messageElement = document.getElementById('notificationModalMessage');
    const button = document.getElementById('notificationModalButton');

    // Determine configuration based on type
    const isSuccess = type === 'success';
    const config = {
        headerClass: isSuccess ? 'modal-header-success' : 'modal-header-error',
        title: isSuccess ? 'Operación Exitosa' : 'Error en Operación',
        headerIconClass: isSuccess ? 'bi-check-circle-fill' : 'bi-exclamation-triangle-fill',
        bodyIconClass: isSuccess ? 'bi-check-circle-fill icon-success' : 'bi-exclamation-triangle-fill icon-error',
        buttonClass: isSuccess ? 'btn-success-custom' : 'btn-danger-custom'
    };

    // Reset all classes
    header.className = 'modal-header';
    headerIcon.className = 'me-2';
    bodyIcon.className = 'notification-icon';
    button.className = 'btn btn-lg w-100';

    // Apply new classes
    header.classList.add(config.headerClass);
    headerIcon.classList.add(config.headerIconClass);
    bodyIcon.classList.add(...config.bodyIconClass.split(' '));
    button.classList.add(config.buttonClass);

    // Set content
    titleText.textContent = config.title;
    messageElement.textContent = message;

    // Show modal
    const bsModal = new bootstrap.Modal(modal, {
        backdrop: 'static',
        keyboard: true
    });
    bsModal.show();

    // Focus button after modal is shown for accessibility
    modal.addEventListener('shown.bs.modal', () => {
        button.focus();
    }, { once: true });
}

/**
 * Show success message in modal
 * @param {string} elementId - DEPRECATED - kept for backward compatibility
 * @param {string} message - Success message to display
 */
function showSuccess(elementId, message) {
    // Hide the inline status element (if it exists)
    const element = document.getElementById(elementId);
    if (element) {
        element.style.display = 'none';
    }

    // Show modal notification
    showNotificationModal('success', message);
}

/**
 * Show error message in modal
 * @param {string} elementId - DEPRECATED - kept for backward compatibility
 * @param {string} message - Error message to display
 */
function showError(elementId, message) {
    // Hide the inline status element (if it exists)
    const element = document.getElementById(elementId);
    if (element) {
        element.style.display = 'none';
    }

    // Show modal notification
    showNotificationModal('error', message);
}
