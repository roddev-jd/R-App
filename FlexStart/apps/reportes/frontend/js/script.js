import { appStore } from './store.js';
import { startTourIfFirstVisit, startTour } from './tour.js';
import * as FavoritesManager from './favorites-manager.js';

// Configuración de API base para la integración con el gateway
const API_BASE = '/reportes';

document.addEventListener('DOMContentLoaded', () => {
    const { getState, setState, subscribe } = appStore;

    // --- 1ECTORES DE ELEMENTOS DOM (de tu archivo original) ---
    const initialLoading = document.getElementById('initial-loading');
    const topScroll = document.getElementById('top-scroll');
    const scrollDummy = topScroll.querySelector('.scroll-dummy');
    const dataTableWrapper = document.getElementById('data-table-wrapper');
    const countrySelect = document.getElementById('country-select');
    const descriptionSection = document.getElementById('description-section');
    const descriptionBox = document.getElementById('description-box');
    const blobSelect = document.getElementById('blob-select');
    const appHeader = document.querySelector('.app-header');
    const headerTitleTextSpan = document.getElementById('header-title-text');
    // Botón de carga simplificado (caché inteligente automático)
    const loadDataBtn = document.getElementById('load-data-btn');
    const loadDataButton = loadDataBtn; // Referencia de compatibilidad

    // Elementos de la card de estado de caché
    const cacheStatusCard = document.getElementById('cache-status-card');
    const cacheStatusIcon = document.getElementById('cache-status-icon');
    const cacheStatusTitle = document.getElementById('cache-status-title');
    const cacheStatusDescription = document.getElementById('cache-status-description');
    const statusMessage = document.getElementById('status-message');
    const rowCountMessage = document.getElementById('row-count-message');
    const spinner = document.getElementById('spinner');
    const filterControlsContainer = document.getElementById('filter-controls');
    const columnsListboxContainer = document.getElementById('columns-listbox-container');
    const dataTableHead = document.querySelector('#data-table thead');
    const dataTableBody = document.querySelector('#data-table tbody');
    const paginationContainer = document.getElementById('pagination-container');
    const applyFiltersButton = document.getElementById('apply-filters-button');
    const exportExcelButton = document.getElementById('export-excel-button');
    const exportCsvButton = document.getElementById('export-csv-button');
    const cancelExportButton = document.getElementById('cancel-export-button');
    const tableOptionsDropdown = document.getElementById('table-options-dropdown');
    // Menú de opciones (⋮)
    const optionsMenuButton = document.getElementById('options-menu-button');
    const saveFavoritesOption = document.getElementById('save-favorites-option');
    const loadFavoritesOption = document.getElementById('load-favorites-option');
    const showHelpOption = document.getElementById('show-help-option');
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const themeText = document.getElementById('theme-text');
    const densitySelect = document.getElementById('density-select');

    // Referencias legacy para compatibilidad
    const loadFilterStateButton = loadFavoritesOption;
    const clearAllFiltersButton = document.getElementById('clear-all-filters-button');
    const consoleOutputDiv = document.getElementById('console-output');
    const selectAllColsButton = document.getElementById('select-all-cols-button');
    const deselectAllColsButton = document.getElementById('deselect-all-cols-button');
    const skuHijoFileInput = document.getElementById('sku-hijo-file');
    const uploadSkuHijoButton = document.getElementById('upload-sku-hijo-button');
    const clearSkuHijoButton = document.getElementById('clear-sku-hijo-button');
    const skuHijoStatus = document.getElementById('sku-hijo-status');
    const extendSkuHijoCheckbox = document.getElementById('extend-sku-hijo-checkbox');
    const skuHijoInput = document.getElementById('sku-hijo-input');
    const batchProcessHijoCheckbox = document.getElementById('batch-process-hijo-checkbox');
    const skuPadreFileInput = document.getElementById('sku-padre-file');
    const uploadSkuPadreButton = document.getElementById('upload-sku-padre-button');
    const clearSkuPadreButton = document.getElementById('clear-sku-padre-button');
    const skuPadreStatus = document.getElementById('sku-padre-status');
    const skuPadreInput = document.getElementById('sku-padre-input');
    const batchProcessPadreCheckbox = document.getElementById('batch-process-padre-checkbox');
    const ticketFilterSection = document.getElementById('ticket-filter-section');
    const ticketFilterInput = document.getElementById('ticket-filter-input');
    const ticketFileInput = document.getElementById('ticket-file-input');
    const uploadTicketFileButton = document.getElementById('upload-ticket-file-button');
    const clearTicketFileButton = document.getElementById('clear-ticket-file-button');
    const ticketFileStatus = document.getElementById('ticket-file-status');
    const lineamientoFilterInput = document.getElementById('lineamiento-filter-input');
    const priorityColoringToggle = document.getElementById('priority-coloring-toggle');
    const priorityLegend = document.getElementById('priority-legend');
    const priority1Percent = document.getElementById('priority-1-percent');
    const priority2Percent = document.getElementById('priority-2-percent');
    const priority3Percent = document.getElementById('priority-3-percent');
    const FORMSPREE_URL = "https://formspree.io/f/xovwbyrw";

    const suggestionFab = document.getElementById('suggestion-fab');
    const suggestionModalElement = document.getElementById('suggestionModal');
    const suggestionModal = new bootstrap.Modal(suggestionModalElement);
    const sendSuggestionButton = document.getElementById('send-suggestion-button');
    const suggestionTextArea = document.getElementById('suggestion-text-area');
    const suggestionStatus = document.getElementById('suggestion-status');

    // Referencias del modal de verificación de cache
    const cacheVerificationModalElement = document.getElementById('cacheVerificationModal');
    const cacheVerificationModal = new bootstrap.Modal(cacheVerificationModalElement);
    const verificationDatabaseName = document.getElementById('verification-database-name');
    const verificationLoading = document.getElementById('verification-loading');
    const verificationResult = document.getElementById('verification-result');
    const verificationError = document.getElementById('verification-error');
    const verificationAlert = document.getElementById('verification-alert');
    const verificationIcon = document.getElementById('verification-icon');
    const verificationTitle = document.getElementById('verification-title');
    const verificationMessage = document.getElementById('verification-message');
    const verificationDetails = document.getElementById('verification-details');
    const cacheTimestamp = document.getElementById('cache-timestamp');
    const remoteTimestamp = document.getElementById('remote-timestamp');
    const verificationErrorMessage = document.getElementById('verification-error-message');
    const reloadDataBtn = document.getElementById('reload-data-btn');

    // Referencias del modal de procesamiento por lotes
    const batchProcessModalElement = document.getElementById('batchProcessModal');
    const batchProcessModal = new bootstrap.Modal(batchProcessModalElement, {
        backdrop: 'static',
        keyboard: false
    });
    const batchCurrentSpan = document.getElementById('batch-current');
    const batchTotalSpan = document.getElementById('batch-total');
    const batchProgressBar = document.getElementById('batch-progress-bar');
    const batchProgressText = document.getElementById('batch-progress-text');
    const batchInfoText = document.getElementById('batch-info-text');
    const batchInfoAlert = document.getElementById('batch-info-alert');
    const batchReadyAlert = document.getElementById('batch-ready-alert');
    const batchSpinner = document.getElementById('batch-spinner');
    const batchCancelBtn = document.getElementById('batch-cancel-btn');
    const batchDownloadBtn = document.getElementById('batch-download-btn');
    const batchCompletedSection = document.getElementById('batch-completed-section');
    const batchCompletedTitle = document.getElementById('batch-completed-title');
    const batchCompletedSummary = document.getElementById('batch-completed-summary');
    const batchNotfoundAlert = document.getElementById('batch-notfound-alert');
    const batchNotfoundCount = document.getElementById('batch-notfound-count');
    const batchDownloadNotfoundBtn = document.getElementById('batch-download-notfound-btn');
    const batchCloseBtn = document.getElementById('batch-close-btn');
    const batchStatusTitle = document.getElementById('batch-status-title');
    const fullLoadRecommendationBtn = reloadDataBtn; // Compatibilidad con código antiguo

    // Referencias de favoritos (ya no hay modal, solo botones en menú)

    // Referencias del modal de Quick Actions
    const quickActionsModalElement = document.getElementById('quickActionsModal');
    const quickActionsModal = new bootstrap.Modal(quickActionsModalElement);
    const quickActionChile = document.getElementById('quick-action-chile');
    const quickActionPeru = document.getElementById('quick-action-peru');
    const quickActionFavorites = document.getElementById('quick-action-favorites');

    // Loaded bases panel removed - using persistent cache instead

    // --- CONSTANTES DE LA APLICACIÓN ---
    const INITIAL_APP_TITLE = "Plataforma de Reportes";
    const NO_SELECTION_TITLE = "Seleccione una Fuente de Datos";
    const SOURCE_SPECIFIC_TITLES = { "CHILE": "Universo Chile", "MEJORAS CHILE": "Mejoras Chile", "PERU": "Universo Perú", "DISENO PERU": "Diseño Perú", "REDACCION PERU": "Redacción Perú", "DATA SCRIPT PERU": "Data para Script redacción" };
    const RED_HEADER_SOURCES_LOWER = ['peru', 'diseno peru', 'redaccion peru', 'data script peru'];
    const BLUE_HEADER_SOURCES_LOWER = ['chile', 'mejoras chile'];

    // Bases que soportan cache persistente (deben coincidir con backend)
    const CACHEABLE_BASES = new Set(['UNIVERSO PERU', 'INFO MARCA PROPIA PERU']);

    // --- ESTADO LOCAL MÍNIMO Y CONSTANTES ---
    let sourcesByCountry = {};
    let currentSelectedDisplayColumns = [];
    let logEventSource = null;
    let progressEventSource = null; // SSE connection for data load progress
    let currentPage = 1;
    let serverCacheStatus = null; // Para almacenar el estado del caché del servidor
    let isExporting = false;
    let currentExportAbortController = null;
    let skusNoEncontrados = [];
    let isSyncingScroll = false; // Para evitar loops en sincronización de scroll
    const dataSourceCache = {};
    let currentPriorityInfo = {}; // Almacena información de prioridad de la consulta actual
    
    // ⚡ OPTIMIZACIÓN: Cache de Vista - Almacena estados renderizados completos
    const viewStateCache = {};
    
    // ⚡ OPTIMIZACIÓN: Lazy Loading Progresivo
    const LAZY_LOAD_CHUNK_SIZE = 50;  // Cargar 50 filas a la vez
    const LAZY_LOAD_INITIAL_SIZE = 100; // Mostrar primeras 100 filas inmediatamente
    let lazyLoadObserver = null;
    
    // ⚡ OPTIMIZACIÓN: Debouncing para Filtros
    const DEBOUNCE_DELAY = 300; // 300ms delay para filtros de texto
    const DEBOUNCE_DELAY_SELECT = 100; // 100ms delay para selects
    let filterDebounceTimer = null;
    const pendingFilterUpdates = new Set();
    
    const PAGE_SIZE = 100;

    // --- FUNCIONES DE LA APLICACIÓN ---

    // === SISTEMA DE MENSAJES CONTEXTUALES ===
    /**
     * Muestra un mensaje contextual en la esquina inferior derecha
     * @param {Object} options - Opciones del mensaje
     * @param {string} options.type - Tipo de mensaje: 'info', 'success', 'warning', 'error'
     * @param {string} options.title - Título del mensaje
     * @param {string} options.message - Texto del mensaje
     * @param {Object} options.action - Acción opcional con label y callback
     * @param {number} options.duration - Duración en ms (default: 5000)
     */
    function showContextMessage(options) {
        const {
            type = 'info',
            title,
            message,
            action = null,
            duration = 5000
        } = options;

        // Obtener contenedor
        const container = document.getElementById('context-messages');
        if (!container) {
            console.error('Contenedor de mensajes contextuales no encontrado');
            return;
        }

        // Determinar icono según tipo
        const icons = {
            info: 'bi-info-circle-fill',
            success: 'bi-check-circle-fill',
            warning: 'bi-exclamation-triangle-fill',
            error: 'bi-x-circle-fill'
        };

        const icon = icons[type] || icons.info;

        // Crear elemento del mensaje
        const messageEl = document.createElement('div');
        messageEl.className = `context-message context-message-${type}`;

        // Construir HTML
        let html = `
            <div class="d-flex align-items-start">
                <i class="bi ${icon} me-2"></i>
                <div class="flex-grow-1">
                    ${title ? `<strong>${title}</strong>` : ''}
                    <p class="mb-0 small">${message}</p>
                    ${action ? `<button class="btn btn-sm btn-primary mt-2 action-btn">${action.label}</button>` : ''}
                </div>
                <button type="button" class="btn-close btn-sm ms-2" aria-label="Cerrar"></button>
            </div>
        `;

        messageEl.innerHTML = html;

        // Event listener para el botón de cerrar
        const closeBtn = messageEl.querySelector('.btn-close');
        closeBtn.addEventListener('click', () => {
            removeMessage(messageEl);
        });

        // Event listener para el botón de acción (si existe)
        if (action && action.callback) {
            const actionBtn = messageEl.querySelector('.action-btn');
            actionBtn.addEventListener('click', () => {
                action.callback();
                removeMessage(messageEl);
            });
        }

        // Agregar al contenedor
        container.appendChild(messageEl);

        // Auto-remover después de duration
        if (duration > 0) {
            setTimeout(() => {
                removeMessage(messageEl);
            }, duration);
        }

        console.log(`📢 Mensaje contextual mostrado: ${type} - ${title || message}`);
    }

    /**
     * Remueve un mensaje contextual con animación
     * @param {HTMLElement} messageEl - Elemento del mensaje a remover
     */
    function removeMessage(messageEl) {
        if (!messageEl || !messageEl.parentNode) return;

        // Agregar clase para animación de salida
        messageEl.classList.add('fade-out');

        // Remover del DOM después de la animación
        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.remove();
            }
        }, 300);
    }

    // === SISTEMA DE INDICADORES DE PROGRESO ===
    /**
     * Muestra el estado de loading en un botón
     * @param {HTMLElement} button - El botón a modificar
     */
    function showButtonLoading(button) {
        if (!button) return;

        // Ocultar contenido normal
        const btnContent = button.querySelector('.btn-content');
        const btnSpinner = button.querySelector('.btn-spinner');

        if (btnContent) btnContent.style.display = 'none';
        if (btnSpinner) btnSpinner.style.display = 'flex';

        // Agregar clase de loading
        button.classList.add('btn-loading');
        button.disabled = true;
    }

    /**
     * Oculta el estado de loading en un botón
     * @param {HTMLElement} button - El botón a modificar
     */
    function hideButtonLoading(button) {
        if (!button) return;

        // Mostrar contenido normal
        const btnContent = button.querySelector('.btn-content');
        const btnSpinner = button.querySelector('.btn-spinner');

        if (btnContent) btnContent.style.display = '';
        if (btnSpinner) btnSpinner.style.display = 'none';

        // Remover clase de loading
        button.classList.remove('btn-loading');
    }

    // === SKELETON SCREENS ===
    /**
     * Muestra skeleton screen en la tabla mientras se cargan datos
     * @param {number} rows - Número de filas skeleton a mostrar (default: 5)
     * @param {number} cols - Número de columnas skeleton a mostrar (default: 8)
     */
    function showTableSkeleton(rows = 5, cols = 8) {
        if (!dataTableBody) return;

        // Limpiar tabla
        dataTableBody.innerHTML = '';
        if (dataTableHead) dataTableHead.innerHTML = '';

        // Crear header skeleton
        if (dataTableHead) {
            const headerRow = document.createElement('tr');
            for (let i = 0; i < cols; i++) {
                const th = document.createElement('th');
                th.innerHTML = '<div class="skeleton-cell skeleton-cell-md"></div>';
                headerRow.appendChild(th);
            }
            dataTableHead.appendChild(headerRow);
        }

        // Crear filas skeleton
        for (let i = 0; i < rows; i++) {
            const tr = document.createElement('tr');
            for (let j = 0; j < cols; j++) {
                const td = document.createElement('td');
                // Variar ancho para realismo
                const widthClass = j === 0 ? 'skeleton-cell-sm' :
                                  j === cols - 1 ? 'skeleton-cell-md' :
                                  'skeleton-cell-lg';
                td.innerHTML = `<div class="skeleton-cell ${widthClass}"></div>`;
                tr.appendChild(td);
            }
            dataTableBody.appendChild(tr);
        }

        // Agregar clase al contenedor de la tabla
        const dataTable = document.getElementById('data-table');
        if (dataTable) {
            dataTable.classList.add('table-skeleton');
        }

        console.log(`💀 Skeleton screen mostrado: ${rows} filas x ${cols} columnas`);
    }

    /**
     * Oculta el skeleton screen de la tabla
     */
    function hideTableSkeleton() {
        const dataTable = document.getElementById('data-table');
        if (dataTable) {
            dataTable.classList.remove('table-skeleton');
        }
    }

    // === SISTEMA DE TOOLTIPS ===
    // Función para inicializar todos los tooltips de Bootstrap
    function initializeTooltips() {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el, {
            delay: { show: 500, hide: 100 }, // Delay para evitar tooltips molestos
            trigger: 'hover focus',
            html: true // Permitir HTML en tooltips
        }));
        console.log(`✓ Inicializados ${tooltipList.length} tooltips`);
        return tooltipList;
    }

    // Función para actualizar tooltip de un botón según su estado
    function updateButtonTooltip(buttonElement, isDisabled, enabledText, disabledReason) {
        if (!buttonElement) return;

        // Determinar el texto del tooltip
        const tooltipText = isDisabled ? `No disponible: ${disabledReason}` : enabledText;

        // Actualizar el atributo title
        buttonElement.setAttribute('title', tooltipText);
        buttonElement.setAttribute('data-bs-original-title', tooltipText);

        // Recrear tooltip de Bootstrap si ya existía
        const existingTooltip = bootstrap.Tooltip.getInstance(buttonElement);
        if (existingTooltip) {
            existingTooltip.dispose();
        }

        // Solo crear nuevo tooltip si tiene data-bs-toggle
        if (buttonElement.hasAttribute('data-bs-toggle') &&
            buttonElement.getAttribute('data-bs-toggle') === 'tooltip') {
            new bootstrap.Tooltip(buttonElement, {
                delay: { show: 500, hide: 100 },
                trigger: 'hover focus',
                html: true
            });
        }
    }

    // Función para mostrar notificación de problemas de conectividad
    function showConnectivityWarning(errorType) {
        const warningDiv = document.createElement('div');
        warningDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 450px;';

        let message = '';
        let alertClass = 'alert-warning';

        switch(errorType) {
            case 'offline':
                // Pérdida de conexión a internet detectada por el navegador
                alertClass = 'alert-danger';
                message = `
                    <i class="bi bi-wifi-off"></i>
                    <strong>Sin Conexión a Internet</strong><br>
                    Tu computadora perdió la conexión a internet.<br><br>
                    <strong>Soluciones:</strong><br>
                    • Verifica tu conexión WiFi o cable de red<br>
                    • Revisa el router o modem<br>
                    • Contacta a tu proveedor de internet si persiste
                `;
                break;

            case 'server_unavailable':
                // Servidor local no está corriendo
                alertClass = 'alert-danger';
                message = `
                    <i class="bi bi-server"></i>
                    <strong>Servidor No Disponible</strong><br>
                    El servidor de la aplicación no está corriendo o se detuvo.<br><br>
                    <strong>Soluciones:</strong><br>
                    • Verifica que el lanzador esté activo<br>
                    • Reinicia la aplicación desde lanzador.py<br>
                    • Contacta soporte si el problema persiste
                `;
                break;

            case 'connection_reset':
                // Servidor cerró la conexión inesperadamente
                alertClass = 'alert-warning';
                message = `
                    <i class="bi bi-arrow-repeat"></i>
                    <strong>Conexión Interrumpida</strong><br>
                    El servidor cerró la conexión durante la operación.<br><br>
                    <strong>Soluciones:</strong><br>
                    • Intenta recargar la página (F5)<br>
                    • Verifica que el servidor no se haya reiniciado<br>
                    • Si persiste, contacta soporte técnico
                `;
                break;

            case 'firewall_blocked':
                // Posible bloqueo por firewall/antivirus
                alertClass = 'alert-warning';
                message = `
                    <i class="bi bi-shield-exclamation"></i>
                    <strong>Conexión Bloqueada</strong><br>
                    Firewall o antivirus puede estar bloqueando la conexión local.<br><br>
                    <strong>Soluciones:</strong><br>
                    • Verifica configuración de firewall de Windows<br>
                    • Revisa tu antivirus (permite conexiones a puerto 8005)<br>
                    • Contacta IT para configurar excepciones<br>
                    • Intenta desactivar temporalmente el firewall para probar
                `;
                break;

            case 'server_error':
                // Error interno del servidor
                alertClass = 'alert-danger';
                message = `
                    <i class="bi bi-exclamation-triangle-fill"></i>
                    <strong>Error del Servidor</strong><br>
                    El servidor encontró un error interno al procesar la solicitud.<br><br>
                    <strong>Soluciones:</strong><br>
                    • Revisa los logs del servidor<br>
                    • Reinicia la aplicación<br>
                    • Contacta soporte técnico con detalles del error
                `;
                break;

            default:
                // Error genérico
                alertClass = 'alert-warning';
                message = `
                    <i class="bi bi-exclamation-triangle-fill"></i>
                    <strong>Error de Conexión</strong><br>
                    Problema detectado en la comunicación con el servidor.<br>
                    Intenta recargar la página o contacta soporte técnico.
                `;
        }

        warningDiv.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
        warningDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(warningDiv);

        // Auto-ocultar después de 25 segundos (más tiempo para mensajes más detallados)
        setTimeout(() => {
            if (warningDiv && warningDiv.parentNode) {
                warningDiv.remove();
            }
        }, 25000);
    }

    // Función para generar reporte de diagnóstico
    function generateNetworkDiagnostics(error, endpoint, userAgent = navigator.userAgent) {
        const diagnostics = {
            timestamp: new Date().toISOString(),
            error: {
                message: error.message,
                name: error.name,
                stack: error.stack?.substring(0, 200) // Limitar tamaño
            },
            endpoint: endpoint,
            network: {
                online: navigator.onLine,
                connection: navigator.connection ? {
                    effectiveType: navigator.connection.effectiveType,
                    downlink: navigator.connection.downlink,
                    rtt: navigator.connection.rtt
                } : 'unavailable'
            },
            browser: {
                userAgent: userAgent.substring(0, 100), // Limitar tamaño
                language: navigator.language,
                platform: navigator.platform
            },
            session: {
                url: window.location.href,
                referrer: document.referrer.substring(0, 100) // Limitar tamaño
            }
        };
        
        // Registrar en consola para debug
        console.group('🔍 Network Diagnostics Report');
        console.error('Error details:', diagnostics.error);
        console.info('Network info:', diagnostics.network);
        console.info('Browser info:', diagnostics.browser);
        console.groupEnd();
        
        // Enviar diagnósticos al servidor (sin bloquear la UI)
        setTimeout(() => {
            try {
                fetch(`${API_BASE}/api/diagnostics/network`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(diagnostics)
                }).catch(() => {}); // Fallar silenciosamente
            } catch (e) {
                // Ignorar errores de envío de diagnósticos
            }
        }, 100);
        
        return diagnostics;
    }

    // Monitor de conectividad de red
    function initNetworkMonitor() {
        let wasOffline = false;
        
        function handleOnline() {
            if (wasOffline) {
                logToBrowserConsole('Conexión a internet restaurada. Reintentando operaciones...', 'info');
                
                // Mostrar notificación de reconexión
                const reconnectDiv = document.createElement('div');
                reconnectDiv.className = 'alert alert-success alert-dismissible fade show position-fixed';
                reconnectDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 350px;';
                reconnectDiv.innerHTML = `
                    <i class="bi bi-wifi"></i>
                    <strong>Conectividad Restaurada</strong><br>
                    La conexión a internet se ha restaurado.
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                document.body.appendChild(reconnectDiv);
                
                setTimeout(() => {
                    if (reconnectDiv && reconnectDiv.parentNode) {
                        reconnectDiv.remove();
                    }
                }, 5000);
                
                // Reintentar conexión de logs si falló
                if (!logEventSource || logEventSource.readyState === EventSource.CLOSED) {
                    setTimeout(() => connectToLogStream(), 1000);
                }
                
                wasOffline = false;
            }
        }
        
        function handleOffline() {
            wasOffline = true;
            logToBrowserConsole('Conexión a internet perdida. Las operaciones se reintentarán automáticamente.', 'warning');

            // Usar la función mejorada de notificaciones
            showConnectivityWarning('offline');
        }
        
        // Registrar event listeners
        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);
        
        // Check inicial del estado
        if (!navigator.onLine) {
            wasOffline = true;
        }
    }

    // Función utilitaria para reintentos de fetch con backoff exponencial
    async function fetchWithRetry(url, options = {}, maxRetries = 3, initialDelay = 1000) {
        let lastError;
        
        // Configuraciones para mejorar estabilidad de conexión
        const defaultOptions = {
            headers: {
                'Connection': 'keep-alive',
                'Keep-Alive': 'timeout=60, max=1000',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                ...options.headers
            },
            credentials: 'same-origin',
            mode: 'cors'
        };
        
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                const controller = new AbortController();
                let timeoutId = null;
                
                // Solo aplicar timeout si se especifica uno
                if (options.timeout && options.timeout > 0) {
                    const timeoutMs = options.timeout;
                    timeoutId = setTimeout(() => {
                        controller.abort(new Error(`Request timeout after ${timeoutMs/1000}s`));
                    }, timeoutMs);
                }
                
                const response = await fetch(url, {
                    ...defaultOptions,
                    ...options,
                    signal: controller.signal,
                    headers: {
                        ...defaultOptions.headers,
                        ...options.headers
                    }
                });
                
                if (timeoutId) clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                return response;
            } catch (error) {
                lastError = error;
                
                if (attempt === maxRetries) {
                    break; // No más reintentos
                }
                
                // Determinar si el error justifica un reintento
                const isRetryableError = 
                    error.name === 'TypeError' ||  // Network error
                    (error.name === 'AbortError' && error.message && error.message.includes('timeout')) ||  // Solo timeouts
                    (error.message && error.message.includes('ERR_CONNECTION')) ||
                    (error.message && error.message.includes('HTTP 5')); // 5xx errors
                
                if (!isRetryableError) {
                    break; // No reintentar para errores no recuperables
                }
                
                const delay = initialDelay * Math.pow(2, attempt);
                logToBrowserConsole(`Intento ${attempt + 1} falló: ${error.message}. Reintentando en ${delay}ms...`, 'warning');
                
                // Generar diagnósticos en el último intento fallido
                if (attempt === maxRetries - 1) {
                    generateNetworkDiagnostics(error, url);
                }
                
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
        
        throw lastError;
    }

    function logToBrowserConsole(message, type = 'info', data = null) {
        const time = new Date().toLocaleTimeString();
        
        // Mapear tipos de log a métodos válidos de console
        const consoleMethod = {
            'info': 'info',
            'warning': 'warn',
            'warn': 'warn',
            'error': 'error',
            'debug': 'log',
            'log': 'log'
        }[type] || 'log';
        
        console[consoleMethod](`[FE][${time}] ${message}`, data || '');
    }



    // ---3FUNCIÓN DE VERIFICACIÓN DE SERVIDOR ---
    async function checkServerReady() {
        try {
            const response = await fetchWithRetry(`${API_BASE}/api/health`, { 
                method: 'GET', 
                timeout: 5000 
            }, 3, 2000);
            if (response.ok) {
                // Servidor está listo, ocultar página de carga inicial
                if (initialLoading) {
                    initialLoading.style.opacity = '0';
                    setTimeout(() => {
                        initialLoading.style.display = 'none';
                    }, 300);
                }
                return true;
            }
        } catch (error) {
            console.log('Servidor aún no está listo, reintentando...');
        }
        return false;
    }

    // Verificar servidor cada 2 segundos hasta que esté listo
    async function waitForServer() {
        let attempts = 0;
        const maxAttempts = 30; // máximo
        
        const checkInterval = setInterval(async () => {
            attempts++;
            const isReady = await checkServerReady();
            
            if (isReady) {
                clearInterval(checkInterval);
                console.log('Servidor listo, iniciando aplicación...');
                // Inicializar la aplicación después de verificar que el servidor esté listo
                init();
            } else if (attempts >= maxAttempts) {
                clearInterval(checkInterval);
                console.error('Timeout: El servidor no respondió en el tiempo esperado');
                if (initialLoading) {
                    const loadingMessage = initialLoading.querySelector('.loading-message');
                    const loadingSubmessage = initialLoading.querySelector('.loading-submessage');
                    
                    if (loadingMessage) loadingMessage.textContent = 'Error: Servidor no disponible';
                    if (loadingSubmessage) {
                        loadingSubmessage.innerHTML = `
                            <strong>Posibles soluciones:</strong><br>
                            • Recarga la página (F5)<br>
                            • Verifica tu conexión a internet<br>
                            • Contacta al administrador del sistema si el problema persiste<br>
                            • Verifica que no haya restricciones de firewall
                        `;
                    }
                    
                    // Agregar botón de reintento
                    const retryButton = document.createElement('button');
                    retryButton.className = 'btn btn-primary mt-3';
                    retryButton.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Reintentar conexión';
                    retryButton.onclick = () => {
                        location.reload();
                    };
                    if (loadingSubmessage && !initialLoading.querySelector('.btn-primary')) {
                        loadingSubmessage.appendChild(retryButton);
                    }
                }
            } else {
                // Actualizar mensaje de progreso
                if (initialLoading) {
                    const progressMessage = initialLoading.querySelector('.loading-submessage');
                    progressMessage.textContent = `Esperando que el servidor esté listo... (${attempts}/${maxAttempts})`;
                }
            }
        }, 200);
    }

    // Iniciar verificación del servidor
    waitForServer();

    // Agregar al inicio del archivo, después de las declaraciones de variables
    const loadingOverlay = document.getElementById('loading-overlay');
    // NOTA: Los siguientes elementos ya no existen en el HTML moderno (sistema de cards)
    // Se mantienen comentados por compatibilidad con código legacy
    // const loadingMessage = document.getElementById('loading-message');
    // const loadingSubmessage = document.getElementById('loading-submessage');
    // const loadingPercentage = document.getElementById('loading-percentage');

    // --- 4FUNCIONES DE LA APLICACIÓN ---
    function setInterfaceState(disabled) {
        const elements = document.querySelectorAll('button:not(#country-select):not(#blob-select), select:not(#country-select):not(#blob-select), input:not(#country-select):not(#blob-select), .filter-select:not(#country-select):not(#blob-select)');
        elements.forEach(element => {
            if (element.id !== 'country-select' &&
                element.id !== 'blob-select') {
                element.disabled = disabled;
            }
        });
    }

    // Función para mostrar/ocultar el overlay
    function toggleLoadingOverlay(show, message = '', submessage = '', percentage = 0) {
        if (show) {
            // Actualizar título del overlay moderno (si existe)
            const loadingTitle = document.getElementById('loading-title');
            if (loadingTitle && message) {
                loadingTitle.textContent = message;
            }

            // Mostrar overlay
            loadingOverlay.style.display = 'flex';
            setTimeout(() => {
                loadingOverlay.style.opacity = '1';
            }, 0);
        } else {
            loadingOverlay.style.opacity = '0';
            setTimeout(() => {
                loadingOverlay.style.display = 'none';
            }, 300);
        }
    }

    function updateLoadingPercentage(percentage) {
        // Esta función ya no es necesaria con el nuevo sistema de cards
        // Se mantiene vacía para evitar errores en código que la llame
        // El progreso ahora se muestra mediante cards de eventos
    }

    // ========================================
    // SISTEMA DE CARDS APILADAS PARA EVENTOS
    // ========================================

    // Mapeo de etapas del backend a mensajes amigables con iconos
    const STAGE_MESSAGES = {
        'init': { icon: '🚀', message: 'Iniciando carga de datos...' },
        'verifying': { icon: '🔍', message: 'Verificando actualizaciones disponibles...' },
        'cache': { icon: '⚡', message: 'Cargando desde caché local...' },
        'download': { icon: '📥', message: 'Descargando desde el servidor...' },
        'processing': { icon: '⚙️', message: 'Procesando información...' },
        'filtering': { icon: '🔍', message: 'Aplicando filtros y validaciones...' },
        'enrichment': { icon: '✨', message: 'Enriqueciendo datos...' },
        'finalizing': { icon: '🎯', message: 'Preparando visualización...' },
        'caching': { icon: '💾', message: 'Guardando en caché...' },
        'complete': { icon: '✅', message: 'Carga completada exitosamente!' },
        'error': { icon: '❌', message: 'Error en la carga' }
    };

    /**
     * Añade una nueva card de evento al stack
     * @param {string} stage - Identificador de la etapa (init, download, processing, etc.)
     * @param {string} customMessage - Mensaje personalizado (opcional, usa el mensaje por defecto si no se proporciona)
     */
    function addEventCard(stage, customMessage = null) {
        const eventsStack = document.getElementById('events-stack');
        if (!eventsStack) {
            console.warn('events-stack no encontrado');
            return;
        }

        const stageConfig = STAGE_MESSAGES[stage] || { icon: '📌', message: 'Procesando...' };

        // Log de advertencia si se usa un stage desconocido (ayuda en debugging)
        if (!STAGE_MESSAGES[stage]) {
            console.warn(`Stage desconocido recibido: '${stage}' - usando fallback. Considera agregarlo a STAGE_MESSAGES.`);
        }

        // Marcar la card actual anterior como completada
        const currentCard = eventsStack.querySelector('.event-card.current');
        if (currentCard) {
            currentCard.classList.remove('current');
            currentCard.classList.add('completed');
        }

        // Crear nueva card
        const card = document.createElement('div');
        card.className = stage === 'error' ? 'event-card error' : 'event-card current';
        card.innerHTML = `
            <span class="event-icon">${stageConfig.icon}</span>
            <span class="event-message">${customMessage || stageConfig.message}</span>
            <span class="event-spinner">⚙️</span>
        `;

        eventsStack.appendChild(card);

        // Auto-scroll suave al final para mostrar la última card
        eventsStack.scrollTo({
            top: eventsStack.scrollHeight,
            behavior: 'smooth'
        });

        logToBrowserConsole(`Card añadida: ${stage} - ${customMessage || stageConfig.message}`, 'debug');
    }

    /**
     * Limpia todas las cards del stack de eventos
     */
    function clearEventCards() {
        const eventsStack = document.getElementById('events-stack');
        if (eventsStack) {
            eventsStack.innerHTML = '';
            logToBrowserConsole('Cards de eventos limpiadas', 'debug');
        }
    }

    /**
     * Marca la card actual como completada sin añadir una nueva
     */
    function markCurrentAsCompleted() {
        const eventsStack = document.getElementById('events-stack');
        if (eventsStack) {
            const currentCard = eventsStack.querySelector('.event-card.current');
            if (currentCard) {
                currentCard.classList.remove('current');
                currentCard.classList.add('completed');
            }
        }
    }

    /**
     * Procesa un mensaje SSE de progreso y actualiza las cards correspondientes
     * @param {Object} progressData - Datos del evento SSE parseados
     */
    function handleProgressEvent(progressData) {
        if (progressData.type === 'progress') {
            const stage = progressData.stage || 'processing';
            const message = progressData.message || 'Procesando...';

            // Añadir card con mensaje limpio (sin tiempo concatenado)
            // El spinner animado indicará que está en proceso
            addEventCard(stage, message);

            logToBrowserConsole(`Progreso: ${stage} - ${message}`, 'info');
        } else if (progressData.type === 'complete') {
            const message = progressData.message || 'Carga completada exitosamente!';

            // Card de completado no necesita spinner
            addEventCard('complete', message);

            // Marcar como completada después de 1 segundo
            setTimeout(() => {
                markCurrentAsCompleted();
            }, 1000);

            logToBrowserConsole(`Carga completada: ${message}`, 'success');
        } else if (progressData.type === 'error') {
            const errorMsg = progressData.message || 'Error en la carga';
            addEventCard('error', errorMsg);
            logToBrowserConsole(`Error de progreso: ${errorMsg}`, 'error');
        }
    }

    function subscribeToStoreChanges() {
        subscribe((state, prevState) => {
            // Manejar estado de carga y overlay
            if (state.loadingDetails.isProcessing !== prevState.loadingDetails.isProcessing) {
                setInterfaceState(state.loadingDetails.isProcessing);
                toggleLoadingOverlay(
                    state.loadingDetails.isProcessing,
                    state.loadingDetails.message,
                    state.loadingDetails.submessage
                );
            }
            
            // Actualizar mensaje de estado
            if (statusMessage && state.statusMessage !== prevState.statusMessage) {
                statusMessage.textContent = state.statusMessage;
            }
            
            // Manejar indicadores de carga
            if (state.isLoading !== prevState.isLoading) {
                spinner.style.display = state.isLoading ? 'inline-block' : 'none';
            }
            
            // Actualizar contador de filas
            if (rowCountMessage && state.rowCount !== prevState.rowCount) {
                let msg = new Intl.NumberFormat('es-CL').format(state.rowCount.display);
                if (state.rowCount.original > 0) {
                    msg += ` / ${new Intl.NumberFormat('es-CL').format(state.rowCount.original)}`;
                }
                rowCountMessage.textContent = msg;
            }

            // Habilitar/deshabilitar botones basado en si hay datos
            const hasData = state.currentBlobDisplayName !== null;
            const hasCachedData = hasData && dataSourceCache[state.currentBlobDisplayName];
            
            // "Carga Completa" siempre disponible si hay una fuente seleccionada
            if (loadDataButton) {
                loadDataButton.disabled = !hasData || state.loadingDetails.isProcessing;
            }

            // Ya no hay botones de dropdown (Carga Rápida, Verificar Caché)
            // El sistema ahora usa un solo botón con caché inteligente automático

            // Otros botones solo disponibles si hay datos
            const buttons = [
                applyFiltersButton,
                exportExcelButton,
                exportCsvButton,
                saveFavoritesOption,
                clearAllFiltersButton,
                loadFilterStateButton,
            ];
            buttons.forEach(btn => { 
                if (btn && !state.loadingDetails.isProcessing) {
                    btn.disabled = !hasData;
                }
            });
        });
    }


    function manageDualScroll() {
        if (!topScroll || !dataTableWrapper || !scrollDummy) return;
        const hasOverflow = dataTableWrapper.scrollWidth > dataTableWrapper.clientWidth;
        topScroll.style.display = hasOverflow ? 'block' : 'none';
        if (hasOverflow) {
            scrollDummy.style.width = `${dataTableWrapper.scrollWidth}px`;
        }
    }

    function renderPagination(totalRows) {
        if (!paginationContainer) return;
        paginationContainer.innerHTML = '';
        const totalPages = Math.ceil(totalRows / PAGE_SIZE);
        if (totalPages <= 1) return;
        const prev = document.createElement('button');
        prev.className = 'btn btn-outline-secondary btn-sm me-2';
        prev.textContent = 'Anterior';
        prev.disabled = currentPage === 1;
        prev.addEventListener('click', () => changePage(currentPage - 1));
        const next = document.createElement('button');
        next.className = 'btn btn-outline-secondary btn-sm ms-2';
        next.textContent = 'Siguiente';
        next.disabled = currentPage === totalPages;
        next.addEventListener('click', () => changePage(currentPage + 1));
        const info = document.createElement('span');
        info.className = 'align-self-center';
        info.textContent = `Página ${currentPage} de ${totalPages}`;
        paginationContainer.append(prev, info, next);
    }

    // --- FUNCIÓN AGREGADA: renderDataTable ---
    function renderDataTable(data, columns) {
        if (!dataTableHead || !dataTableBody) return;
        
        // Renderizar encabezados
        dataTableHead.innerHTML = '';
        if (Array.isArray(columns) && columns.length > 0) {
            const headerRow = document.createElement('tr');
            columns.forEach(col => {
                const th = document.createElement('th');
                th.textContent = col;
                headerRow.appendChild(th);
            });
            dataTableHead.appendChild(headerRow);
        }
        
        // Limpiar body de la tabla
        dataTableBody.innerHTML = '';
        
        if (!Array.isArray(data) || data.length === 0) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = columns.length || 1;
            td.className = 'text-center text-muted p-3';
            td.textContent = 'No hay datos para mostrar.';
            tr.appendChild(td);
            dataTableBody.appendChild(tr);
            return;
        }

        // ⚡ OPTIMIZACIÓN: Lazy Loading Progresivo
        if (data.length > LAZY_LOAD_INITIAL_SIZE) {
            logToBrowserConsole(`Aplicando lazy loading: mostrando ${LAZY_LOAD_INITIAL_SIZE} de ${data.length} filas inicialmente`);

            // Renderizar solo las primeras filas
            const initialData = data.slice(0, LAZY_LOAD_INITIAL_SIZE);
            renderTableRows(initialData, columns, 0);

            // Configurar lazy loading para el resto
            initializeLazyLoading();
            setupLazyLoadTrigger();

            logToBrowserConsole(`Lazy loading configurado para ${data.length - LAZY_LOAD_INITIAL_SIZE} filas restantes`, 'debug');

        } else {
            // Renderizar todas las filas si son pocas
            renderTableRows(data, columns, 0);
            logToBrowserConsole(`Renderizado completo: ${data.length} filas (sin lazy loading)`, 'debug');
        }

        // Actualizar scroll superior después del renderizado
        setTimeout(() => manageDualScroll(), 0);
    }

    // ⚡ FUNCIÓN AUXILIAR: Renderizar filas de tabla
    function renderTableRows(rowsData, columns, startIndex) {
        if (!dataTableBody) return;
        
        rowsData.forEach((row, index) => {
            const tr = document.createElement('tr');
            tr.setAttribute('data-row-index', startIndex + index);
            
            // Aplicar coloreado por prioridad si está habilitado
            applyPriorityColoring(tr, startIndex + index, row);
            
            columns.forEach(col => {
                const td = document.createElement('td');
                const value = row[col] !== undefined ? row[col] : '';
                
                // ⚡ OPTIMIZACIÓN: Formateo inteligente de datos
                if (col.toLowerCase().includes('fecha') && value) {
                    try {
                        const date = new Date(value);
                        if (!isNaN(date.getTime())) {
                            td.textContent = date.toLocaleDateString();
                        } else {
                            td.textContent = value;
                        }
                    } catch (e) {
                        td.textContent = value;
                    }
                } else if (typeof value === 'number' && col.toLowerCase().includes('precio')) {
                    td.textContent = value.toLocaleString();
                } else {
                    td.textContent = value;
                }
                
                tr.appendChild(td);
            });
            
            dataTableBody.appendChild(tr);
        });
    }

    // NUEVA FUNCIÓN: Aplicar coloreado por prioridad a una fila
    function applyPriorityColoring(trElement, rowIndex, rowData) {
        // Verificar si el coloreado por prioridad está habilitado
        if (!priorityColoringToggle || !priorityColoringToggle.checked) return;
        
        // Verificar si hay información de prioridad disponible
        if (!currentPriorityInfo || !currentPriorityInfo.has_priority_column) return;
        
        // Buscar el valor de prioridad para esta fila
        let priorityValue = null;
        
        // Intentar obtener la prioridad desde currentPriorityInfo primero
        if (currentPriorityInfo.row_priorities && currentPriorityInfo.row_priorities[rowIndex] !== undefined) {
            priorityValue = currentPriorityInfo.row_priorities[rowIndex];
        } else {
            // Buscar directamente en los datos de la fila
            const priorityColumn = currentPriorityInfo.column_name;
            if (priorityColumn && rowData[priorityColumn] !== undefined) {
                priorityValue = String(rowData[priorityColumn]).trim().toUpperCase();
            }
        }
        
        // Aplicar clase CSS basada en el valor de prioridad
        if (priorityValue) {
            // Limpiar clases de prioridad existentes
            trElement.className = trElement.className.replace(/priority-row-[123]/g, '');
            
            if (priorityValue.includes('PRIORIDAD_1') || priorityValue.includes('PRIORITY_1')) {
                trElement.classList.add('priority-row-1');
            } else if (priorityValue.includes('PRIORIDAD_2') || priorityValue.includes('PRIORITY_2')) {
                trElement.classList.add('priority-row-2');
            } else if (priorityValue.includes('PRIORIDAD_3') || priorityValue.includes('PRIORITY_3')) {
                trElement.classList.add('priority-row-3');
            }
        }
    }

    // NUEVA FUNCIÓN: Re-aplicar coloreado por prioridad a todas las filas visibles
    function reapplyPriorityColoring() {
        if (!dataTableBody) return;
        
        const tableRows = dataTableBody.querySelectorAll('tr');
        const { dataForDisplay, currentBlobDisplayName } = getState();
        
        // Obtener información de prioridad desde caché si no está en currentPriorityInfo
        let priorityInfo = currentPriorityInfo;
        if ((!priorityInfo || !priorityInfo.has_priority_column) && currentBlobDisplayName && dataSourceCache[currentBlobDisplayName]) {
            const cacheEntry = dataSourceCache[currentBlobDisplayName];
            if (cacheEntry.hasPriorityColumn && cacheEntry.priorityInfo) {
                priorityInfo = cacheEntry.priorityInfo;
                currentPriorityInfo = priorityInfo; // Actualizar la variable global
                logToBrowserConsole('Información de prioridad restaurada desde caché para toggle dinámico', 'debug');
            }
        }
        
        tableRows.forEach((tr, index) => {
            // Limpiar clases de prioridad existentes
            tr.className = tr.className.replace(/priority-row-[123]/g, '');
            
            // Si el toggle está habilitado y hay datos disponibles, aplicar coloreado
            if (priorityColoringToggle && priorityColoringToggle.checked && dataForDisplay && dataForDisplay[index]) {
                // Temporalmente actualizar currentPriorityInfo para applyPriorityColoring
                const originalPriorityInfo = currentPriorityInfo;
                currentPriorityInfo = priorityInfo;
                applyPriorityColoring(tr, index, dataForDisplay[index]);
                currentPriorityInfo = originalPriorityInfo;
            }
        });
        
        // Mostrar/ocultar la leyenda de prioridad
        updatePriorityLegendVisibility();
        
        logToBrowserConsole(`Coloreado por prioridad ${priorityColoringToggle.checked ? 'aplicado' : 'removido'} a ${tableRows.length} filas`, 'info');
    }

    // NUEVA FUNCIÓN: Actualizar visibilidad de la leyenda de prioridad
    function updatePriorityLegendVisibility() {
        if (!priorityLegend) return;
        
        const isToggleChecked = priorityColoringToggle && priorityColoringToggle.checked;
        const hasPriorityData = currentPriorityInfo && currentPriorityInfo.has_priority_column;
        
        logToBrowserConsole(`updatePriorityLegendVisibility - Toggle: ${isToggleChecked}, HasData: ${hasPriorityData}`, 'debug');
        
        if (isToggleChecked && hasPriorityData) {
            priorityLegend.classList.remove('d-none');
            logToBrowserConsole('Leyenda mostrada, actualizando porcentajes...', 'debug');
            updatePriorityPercentages();
        } else {
            priorityLegend.classList.add('d-none');
            logToBrowserConsole('Leyenda ocultada', 'debug');
        }
    }

    // NUEVA FUNCIÓN: Calcular y actualizar porcentajes de prioridad
    function updatePriorityPercentages() {
        logToBrowserConsole('updatePriorityPercentages() llamada', 'debug');
        
        if (!currentPriorityInfo || !currentPriorityInfo.has_priority_column) {
            logToBrowserConsole('No hay currentPriorityInfo o no tiene columna de prioridad', 'debug');
            return;
        }

        // Obtener conteos desde la información de prioridad
        const counts = currentPriorityInfo.priority_counts || {};
        const total1 = counts['PRIORIDAD_1'] || 0;
        const total2 = counts['PRIORIDAD_2'] || 0;
        const total3 = counts['PRIORIDAD_3'] || 0;
        const totalOther = counts['other'] || 0;
        
        const grandTotal = total1 + total2 + total3 + totalOther;
        
        logToBrowserConsole(`Conteos de prioridad - P1: ${total1}, P2: ${total2}, P3: ${total3}, Other: ${totalOther}, Total: ${grandTotal}`, 'info');
        
        if (grandTotal === 0) {
            // Si no hay datos, mostrar 0%
            if (priority1Percent) priority1Percent.textContent = '(0%)';
            if (priority2Percent) priority2Percent.textContent = '(0%)';
            if (priority3Percent) priority3Percent.textContent = '(0%)';
            logToBrowserConsole('Total es 0, mostrando 0% en todos los porcentajes', 'debug');
            return;
        }

        // Calcular porcentajes
        const percent1 = ((total1 / grandTotal) * 100).toFixed(1);
        const percent2 = ((total2 / grandTotal) * 100).toFixed(1);
        const percent3 = ((total3 / grandTotal) * 100).toFixed(1);

        // Actualizar elementos DOM
        if (priority1Percent) priority1Percent.textContent = `(${percent1}%)`;
        if (priority2Percent) priority2Percent.textContent = `(${percent2}%)`;
        if (priority3Percent) priority3Percent.textContent = `(${percent3}%)`;

        logToBrowserConsole(`✅ Porcentajes de prioridad actualizados - P1: ${percent1}%, P2: ${percent2}%, P3: ${percent3}%`, 'info');
    }

    function changePage(newPage) {
        const totalPages = Math.ceil(getState().rowCount.filtered / PAGE_SIZE);
        if (newPage >= 1 && newPage <= totalPages) {
            currentPage = newPage;
            handleApplyFilters(newPage);
        }
    }

    function updateHeaderStyle(selectedDisplayName, isInitialAppLoadState = false) {
        if (!appHeader || !headerTitleTextSpan) return;
        let newTitle = "";
        appHeader.classList.remove('app-header-purple', 'app-header-red');
        const displayNameLower = selectedDisplayName ? selectedDisplayName.toLowerCase().trim() : null;
        if (!selectedDisplayName) {
            appHeader.classList.add('app-header-purple');
            newTitle = isInitialAppLoadState ? INITIAL_APP_TITLE : NO_SELECTION_TITLE;
        } else if (RED_HEADER_SOURCES_LOWER.includes(displayNameLower)) {
            appHeader.classList.add('app-header-red');
            newTitle = SOURCE_SPECIFIC_TITLES[selectedDisplayName.toUpperCase()] || selectedDisplayName;
        } else {
            newTitle = SOURCE_SPECIFIC_TITLES[selectedDisplayName.toUpperCase()] || selectedDisplayName;
        }
        if (headerTitleTextSpan.textContent !== newTitle) {
            headerTitleTextSpan.classList.add('fade-out');
            setTimeout(() => {
                headerTitleTextSpan.textContent = newTitle;
                headerTitleTextSpan.classList.remove('fade-out');
            }, 300);
        }
    }

    async function resetUIDataAndFilters() {
        logToBrowserConsole("Reseteando todos los filtros de la UI y los datos de la tabla.");

        // 1. Limpiar filtros de texto y áreas de texto (reutilizando la nueva función)
        clearManualFilterInputs();

        // 2. Resetear los selectores de filtros de columnas
        const selects = filterControlsContainer.querySelectorAll('select');
        selects.forEach(select => {
            if (select.tomselect) {
                select.tomselect.clear();
            } else {
                Array.from(select.options).forEach(option => option.selected = false);
            }
        });

        // 3. Resetear la selección de columnas a mostrar
        if (columnsListboxContainer) {
            const checkboxes = columnsListboxContainer.querySelectorAll('input[type="checkbox"]');
            const { hiddenColumnsConfig } = getState(); // Corregido para obtener del store
            const hiddenCols = hiddenColumnsConfig || [];
            checkboxes.forEach(cb => {
                cb.checked = !hiddenCols.includes(cb.value);
            });
        }
        
        // 4. Limpiar la tabla de datos y paginación
        clearDataTable();
        
        // 5. Resetear contador de filas (se actualiza automáticamente mediante el store)

        // 6. Resetear estado del store relevante
        setState({
            skuHijoFileLoaded: false,
            skuPadreFileLoaded: false,
            // No resetear 'dataForDisplay' o 'currentBlob...' aquí,
            // porque esta función se usa para LIMPIAR, no para descargar un nuevo archivo.
        });
        
        logToBrowserConsole("Reseteo de UI y filtros completado.");
    }

    // ⚡ OPTIMIZACIÓN: Funciones de Cache de Vista
    function saveViewState(blobName) {
        try {
            const table = document.getElementById('data-table');
            const filterContainer = document.getElementById('filter-container');
            const paginationContainer = document.querySelector('.pagination-container');
            
            if (!table || !filterContainer) {
                // Solo log en debug - esto es normal durante la carga inicial
                logToBrowserConsole(`Elementos DOM aún no disponibles para cache de vista de ${blobName}`, 'debug');
                return;
            }

            viewStateCache[blobName] = {
                tableHTML: table.innerHTML,
                filtersHTML: filterContainer.innerHTML,
                paginationHTML: paginationContainer ? paginationContainer.innerHTML : '',
                timestamp: Date.now(),
                // Guardar estado de filtros activos
                filterStates: {
                    skuHijo: skuHijoInput ? skuHijoInput.value : '',
                    skuPadre: skuPadreInput ? skuPadreInput.value : '',
                    ticket: ticketFilterInput ? ticketFilterInput.value : '',
                    lineamiento: lineamientoFilterInput ? lineamientoFilterInput.value : ''
                },
                // Guardar estado actual de la aplicación
                appState: getState()
            };
            
            logToBrowserConsole(`Estado de vista guardado para ${blobName}`, 'debug');
        } catch (error) {
            logToBrowserConsole(`Error guardando estado de vista para ${blobName}: ${error.message}`, 'error');
        }
    }

    function restoreViewState(blobName) {
        const cachedState = viewStateCache[blobName];
        if (!cachedState) {
            return false;
        }

        try {
            const table = document.getElementById('data-table');
            const filterContainer = document.getElementById('filter-container');
            const paginationContainer = document.querySelector('.pagination-container');
            
            if (!table || !filterContainer) {
                logToBrowserConsole(`No se pudo restaurar estado de vista para ${blobName} - elementos DOM faltantes`, 'warn');
                return false;
            }

            // Restaurar contenido HTML
            table.innerHTML = cachedState.tableHTML;
            filterContainer.innerHTML = cachedState.filtersHTML;
            if (paginationContainer && cachedState.paginationHTML) {
                paginationContainer.innerHTML = cachedState.paginationHTML;
            }

            // Restaurar valores de filtros
            setTimeout(() => {
                if (skuHijoInput) skuHijoInput.value = cachedState.filterStates.skuHijo;
                if (skuPadreInput) skuPadreInput.value = cachedState.filterStates.skuPadre;
                if (ticketFilterInput) ticketFilterInput.value = cachedState.filterStates.ticket;
                if (lineamientoFilterInput) lineamientoFilterInput.value = cachedState.filterStates.lineamiento;
            }, 10);

            // Restaurar estado de la aplicación
            setState(cachedState.appState);
            
            logToBrowserConsole(`Estado de vista restaurado para ${blobName}`, 'debug');
            return true;
        } catch (error) {
            logToBrowserConsole(`Error restaurando estado de vista para ${blobName}: ${error.message}`, 'error');
            return false;
        }
    }

    function clearViewStateCache(blobName = null) {
        if (blobName) {
            delete viewStateCache[blobName];
            logToBrowserConsole(`Cache de vista eliminado para ${blobName}`, 'debug');
        } else {
            Object.keys(viewStateCache).forEach(key => delete viewStateCache[key]);
            logToBrowserConsole('Todo el cache de vista ha sido eliminado', 'debug');
        }
    }

    // ⚡ OPTIMIZACIÓN: Funciones de Lazy Loading Progresivo
    function initializeLazyLoading() {
        // Cleanup anterior
        if (lazyLoadObserver) {
            lazyLoadObserver.disconnect();
        }

        // Crear nuevo observer para detectar cuando se llega al final de la tabla
        lazyLoadObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const loadMoreElement = entry.target;
                    loadMoreChunk(loadMoreElement);
                }
            });
        }, {
            rootMargin: '200px' // Cargar cuando está a 200px de llegar al final
        });
    }

    async function loadMoreChunk(loadMoreElement) {
        try {
            // Obtener los datos desde el último renderizado (lo que está actualmente visible en pantalla)
            const response = await fetchWithRetry(`${API_BASE}/api/data/filter`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(getFilterPayload()),
                timeout: 30000
            }, 2, 1500);

            if (!response.ok) {
                throw new Error('Error al obtener más datos');
            }

            const result = await response.json();
            const totalData = result.data || [];
            
            const currentRowCount = document.querySelectorAll('#data-table tbody tr:not(.load-more-trigger-row)').length;
            
            if (currentRowCount >= totalData.length) {
                // Ya se cargaron todos los datos
                loadMoreElement.style.display = 'none';
                logToBrowserConsole(`Lazy loading: todos los datos ya están cargados (${currentRowCount}/${totalData.length})`);
                return;
            }

            // Mostrar indicador de carga
            loadMoreElement.innerHTML = '<td colspan="100%"><div class="loading-more">🔄 Cargando más datos...</div></td>';
            
            // Delay mínimo para UX
            await new Promise(resolve => setTimeout(resolve, 150));
            
            const endIndex = Math.min(currentRowCount + LAZY_LOAD_CHUNK_SIZE, totalData.length);
            const newRows = totalData.slice(currentRowCount, endIndex);
            const columns = result.columns_in_data || [];
            
            // Renderizar nuevas filas usando la función auxiliar
            newRows.forEach((rowData, index) => {
                const tr = document.createElement('tr');
                tr.setAttribute('data-row-index', currentRowCount + index);
                
                columns.forEach(col => {
                    const td = document.createElement('td');
                    const value = rowData[col] !== undefined ? rowData[col] : '';
                    
                    // Aplicar mismo formateo que en renderTableRows
                    if (col.toLowerCase().includes('fecha') && value) {
                        try {
                            const date = new Date(value);
                            if (!isNaN(date.getTime())) {
                                td.textContent = date.toLocaleDateString();
                            } else {
                                td.textContent = value;
                            }
                        } catch (e) {
                            td.textContent = value;
                        }
                    } else if (typeof value === 'number' && col.toLowerCase().includes('precio')) {
                        td.textContent = value.toLocaleString();
                    } else {
                        td.textContent = value;
                    }
                    
                    tr.appendChild(td);
                });
                
                // Insertar antes del trigger row
                dataTableBody.insertBefore(tr, loadMoreElement);
            });

            // Actualizar scroll superior después de añadir filas
            setTimeout(() => manageDualScroll(), 0);

            if (endIndex >= totalData.length) {
                // Completado - ocultar el trigger
                loadMoreElement.style.display = 'none';
                logToBrowserConsole(`Lazy loading completado: ${totalData.length} filas cargadas totales`, 'debug');
            } else {
                // Restaurar el trigger para la próxima carga
                loadMoreElement.innerHTML = '<td colspan="100%"><div class="load-more-trigger" style="height: 1px;"></div></td>';
                logToBrowserConsole(`Lazy loading progreso: ${endIndex}/${totalData.length} filas cargadas`, 'debug');
            }
            
        } catch (error) {
            logToBrowserConsole(`Error en lazy loading: ${error.message}`, 'error');
            loadMoreElement.innerHTML = '<td colspan="100%"><div class="load-error">⚠️ Error cargando más datos</div></td>';
        }
    }

    function renderAdditionalRows(rows, startIndex) {
        const tableBody = document.querySelector('#data-table tbody');
        const loadMoreTrigger = tableBody.querySelector('.load-more-trigger');
        
        if (!tableBody) return;

        rows.forEach((rowData, index) => {
            const row = createTableRow(rowData, startIndex + index);
            if (loadMoreTrigger && loadMoreTrigger.parentElement && loadMoreTrigger.parentElement.parentElement) {
                tableBody.insertBefore(row, loadMoreTrigger.parentElement.parentElement);
            } else {
                tableBody.appendChild(row);
            }
        });
    }

    function createTableRow(rowData, rowIndex) {
        const row = document.createElement('tr');
        row.setAttribute('data-row-index', rowIndex);
        
        // Obtener las columnas visibles actuales
        const { selectedColumns } = getState();
        const columnsToShow = selectedColumns.length > 0 ? selectedColumns : Object.keys(rowData);
        
        columnsToShow.forEach(column => {
            const cell = document.createElement('td');
            const value = rowData[column] || '';
            
            // Aplicar formateo según el tipo de columna
            if (column.toLowerCase().includes('fecha') && value) {
                try {
                    const date = new Date(value);
                    cell.textContent = date.toLocaleDateString();
                } catch (e) {
                    cell.textContent = value;
                }
            } else {
                cell.textContent = value;
            }
            
            row.appendChild(cell);
        });
        
        return row;
    }

    function setupLazyLoadTrigger() {
        const tableBody = document.querySelector('#data-table tbody');
        if (!tableBody) return;

        // Crear fila trigger para lazy loading
        const triggerRow = document.createElement('tr');
        triggerRow.className = 'load-more-trigger-row';
        triggerRow.innerHTML = '<td colspan="100%"><div class="load-more-trigger" style="height: 1px;"></div></td>';
        
        tableBody.appendChild(triggerRow);
        
        // Observar el elemento trigger
        if (lazyLoadObserver) {
            lazyLoadObserver.observe(triggerRow);
        }
    }

    // ⚡ OPTIMIZACIÓN: Funciones de Debouncing
    function debounceFilterUpdate(filterType, delay = DEBOUNCE_DELAY) {
        // Cancelar timer anterior
        if (filterDebounceTimer) {
            clearTimeout(filterDebounceTimer);
        }

        // Agregar este filtro a los pendientes
        pendingFilterUpdates.add(filterType);

        // Mostrar indicador visual de actualización pendiente
        showFilterUpdatePending();

        // Configurar nuevo timer
        filterDebounceTimer = setTimeout(() => {
            logToBrowserConsole(`Ejecutando actualización de filtros debounced: ${Array.from(pendingFilterUpdates).join(', ')}`, 'debug');
            
            // Limpiar indicadores
            hideFilterUpdatePending();
            pendingFilterUpdates.clear();
            
            // Ejecutar actualización
            handleApplyFilters(1, false);
            
        }, delay);
    }

    function showFilterUpdatePending() {
        // Agregar clase visual a la tabla para indicar actualización pendiente
        const table = document.getElementById('data-table');
        if (table && !table.classList.contains('filter-updating')) {
            table.classList.add('filter-updating');
        }

        // Mostrar contador en un elemento de estado (si existe)
        const statusElement = document.querySelector('.filter-status');
        if (statusElement) {
            statusElement.textContent = `⏳ Actualizando filtros... (${pendingFilterUpdates.size} cambios)`;
            statusElement.style.display = 'block';
        }
    }

    function hideFilterUpdatePending() {
        // Quitar clase visual
        const table = document.getElementById('data-table');
        if (table) {
            table.classList.remove('filter-updating');
        }

        // Ocultar elemento de estado
        const statusElement = document.querySelector('.filter-status');
        if (statusElement) {
            statusElement.style.display = 'none';
        }
    }

    // Función para cancelar actualizaciones pendientes (ej: cuando se cambia de base)
    function cancelPendingFilterUpdates() {
        if (filterDebounceTimer) {
            clearTimeout(filterDebounceTimer);
            filterDebounceTimer = null;
        }
        pendingFilterUpdates.clear();
        hideFilterUpdatePending();
        // Limpiar indicadores visuales de campos individuales
        clearAllFilterInputPending();
        logToBrowserConsole('Actualizaciones de filtros pendientes canceladas', 'debug');
    }

    // ⚡ NUEVA FUNCIÓN: Solo mostrar indicador visual sin aplicar filtros
    function showFilterInputPending(inputElement, filterType) {
        if (!inputElement) return;
        
        // Agregar clase visual al campo
        inputElement.classList.add('filter-input-pending');
        
        // Agregar a la lista de pendientes (solo para tracking visual)
        pendingFilterUpdates.add(filterType);
        
        // Actualizar contador visual si existe
        updatePendingFiltersCounter();
        
        logToBrowserConsole(`Campo ${filterType} modificado - esperando aplicación manual`, 'debug');
    }

    // === FUNCIONES PARA CARD DE ESTADO DE CACHÉ (Indicador visual inteligente) ===

    /**
     * Muestra la card de estado de caché con el estado correspondiente
     * @param {string} status - 'verifying' | 'using_cache' | 'downloading_fresh' | 'no_cache'
     */
    function showCacheStatusCard(status) {
        if (!cacheStatusCard) return;

        // Remover clases previas
        cacheStatusCard.classList.remove('using-cache', 'downloading-fresh', 'no-cache', 'verifying', 'hiding');

        // Configurar según el estado
        switch(status) {
            case 'verifying':
                cacheStatusCard.classList.add('verifying');
                cacheStatusIcon.className = 'bi bi-arrow-repeat';
                cacheStatusTitle.textContent = 'Verificando actualizaciones...';
                cacheStatusDescription.textContent = 'Comparando versiones con el servidor';
                logToBrowserConsole('Verificando actualizaciones en el servidor', 'info');
                break;

            case 'using_cache':
                cacheStatusCard.classList.add('using-cache');
                cacheStatusIcon.className = 'bi bi-lightning-charge-fill';
                cacheStatusTitle.textContent = '⚡ Carga Rápida - Usando Caché';
                cacheStatusDescription.textContent = 'Datos cargados desde caché local (actualizado)';
                logToBrowserConsole('✅ Usando caché local - datos actualizados', 'success');
                break;

            case 'downloading_fresh':
                cacheStatusCard.classList.add('downloading-fresh');
                cacheStatusIcon.className = 'bi bi-cloud-download-fill';
                cacheStatusTitle.textContent = '🔄 Descargando Actualización';
                cacheStatusDescription.textContent = 'Nueva versión detectada, descargando desde servidor';
                logToBrowserConsole('🔄 Nueva versión detectada - descargando actualización', 'info');
                break;

            case 'no_cache':
                cacheStatusCard.classList.add('no-cache');
                cacheStatusIcon.className = 'bi bi-database-fill';
                cacheStatusTitle.textContent = 'Carga Completa';
                cacheStatusDescription.textContent = 'Descargando datos desde servidor';
                logToBrowserConsole('📦 Descargando datos desde servidor', 'info');
                break;
        }

        // Mostrar card
        cacheStatusCard.style.display = 'block';

        // Auto-ocultar después de 5 segundos (excepto si está verificando)
        if (status !== 'verifying') {
            setTimeout(() => {
                hideCacheStatusCard();
            }, 5000);
        }
    }

    /**
     * Oculta la card de estado de caché con animación
     */
    function hideCacheStatusCard() {
        if (!cacheStatusCard) return;

        cacheStatusCard.classList.add('hiding');
        setTimeout(() => {
            cacheStatusCard.style.display = 'none';
            cacheStatusCard.classList.remove('hiding');
        }, 300); // Duración de la animación de salida
    }

    // --- FUNCIONES PARA CACHE PERSISTENTE Y VERIFICACIÓN DE ACTUALIZACIONES ---

    // Variable global para trackear el estado del cache persistente
    let persistentCacheStatus = {};

    async function checkPersistentCacheAvailability(blobDisplayName) {
        try {
            logToBrowserConsole(`Verificando disponibilidad de cache persistente para: ${blobDisplayName}`, 'info');
            
            const response = await fetch(`${API_BASE}/api/data/check-updates/${encodeURIComponent(blobDisplayName)}`);
            const result = await response.json();
            
            if (response.ok) {
                // Actualizar estado global del cache persistente
                persistentCacheStatus[blobDisplayName] = {
                    cacheable: result.cacheable,
                    has_cache: result.has_cache,
                    update_available: result.update_available || false
                };

                if (result.cacheable && result.has_cache) {
                    logToBrowserConsole(`Cache persistente encontrado para ${blobDisplayName}`, 'info');

                    // Actualizar disponibilidad de botones
                    updateButtonAvailability();
                }
            }
        } catch (error) {
            logToBrowserConsole(`Error verificando cache persistente: ${error.message}`, 'debug');
        }
    }

    // Funciones para mostrar/ocultar notificaciones de actualización
    function showUpdateNotification() {
        // TODO: Implementar notificación visual de actualización disponible
        // Por ahora, solo registramos en consola
        logToBrowserConsole('💡 Actualización disponible - considera hacer una Carga Completa', 'info');
    }

    function hideUpdateNotification() {
        // TODO: Implementar ocultamiento de notificación
        // Por ahora, función vacía para evitar errores
    }

    async function checkForUpdates(blobDisplayName) {
        try {
            logToBrowserConsole(`Verificando actualizaciones para: ${blobDisplayName}`, 'info');
            
            const response = await fetch(`${API_BASE}/api/data/check-updates/${encodeURIComponent(blobDisplayName)}`);
            const result = await response.json();
            
            if (response.ok) {
                logToBrowserConsole(`Verificación completada para ${blobDisplayName}: ${JSON.stringify(result)}`, 'debug');
                
                // Actualizar estado global del cache persistente
                persistentCacheStatus[blobDisplayName] = {
                    cacheable: result.cacheable,
                    has_cache: result.has_cache,
                    update_available: result.update_available || false
                };

                // MEJORA: Actualizar disponibilidad si hay cache persistente disponible
                if (result.cacheable && result.has_cache) {
                    logToBrowserConsole(`Cache persistente disponible para ${blobDisplayName}`, 'info');

                    // Actualizar disponibilidad de botones
                    updateButtonAvailability();
                }
                
                // Solo mostrar notificación de actualización si hay actualizaciones disponibles
                if (result.update_available && result.has_cache) {
                    showUpdateNotification();
                    logToBrowserConsole(`Actualización disponible para ${blobDisplayName}`, 'info');
                } else {
                    hideUpdateNotification();
                    if (result.has_cache && !result.update_available) {
                        logToBrowserConsole(`Cache está actualizado para ${blobDisplayName}`, 'info');
                    }
                }
            } else {
                logToBrowserConsole(`Error verificando actualizaciones: ${result.detail || result.message}`, 'warning');
                hideUpdateNotification();
            }
        } catch (error) {
            console.warn('Error verificando actualizaciones:', error);
            logToBrowserConsole(`Error verificando actualizaciones: ${error.message}`, 'warning');
            hideUpdateNotification();
        }
    }

    function clearAllFilterInputPending() {
        // Limpiar clases visuales de todos los campos de filtro
        const filterInputs = [skuHijoInput, skuPadreInput, ticketFilterInput, lineamientoFilterInput];
        
        filterInputs.forEach(input => {
            if (input) {
                input.classList.remove('filter-input-pending');
            }
        });
        
        pendingFilterUpdates.clear();
        updatePendingFiltersCounter();
        logToBrowserConsole('Indicadores visuales de filtros limpiados', 'debug');
    }

    function updatePendingFiltersCounter() {
        const applyFiltersButton = document.querySelector('#apply-filters-button');
        
        if (pendingFilterUpdates.size > 0) {
            // Mostrar badge en el botón de aplicar filtros
            if (applyFiltersButton) {
                applyFiltersButton.classList.add('has-pending-filters');
                
                // Actualizar texto del botón para indicar cambios pendientes
                const originalText = applyFiltersButton.getAttribute('data-original-text') || applyFiltersButton.textContent;
                if (!applyFiltersButton.getAttribute('data-original-text')) {
                    applyFiltersButton.setAttribute('data-original-text', originalText);
                }
                applyFiltersButton.innerHTML = `${originalText} <span class="badge bg-warning text-dark ms-1">${pendingFilterUpdates.size}</span>`;
            }
        } else {
            // Limpiar indicadores
            if (applyFiltersButton) {
                applyFiltersButton.classList.remove('has-pending-filters');
                const originalText = applyFiltersButton.getAttribute('data-original-text');
                if (originalText) {
                    applyFiltersButton.textContent = originalText;
                }
            }
        }
    }

    // ⚡ OPTIMIZACIÓN: Función eficiente para limpiar filtros manuales
    function clearManualFilterInputs() {
        const startTime = performance.now();
        let fieldsCleared = 0;
        
        // Cancelar cualquier actualización de filtro pendiente
        cancelPendingFilterUpdates();
        
        // Array de campos a limpiar con sus nombres para logging
        const fieldsToClean = [
            { input: skuHijoInput, name: 'SKU Hijo' },
            { input: skuPadreInput, name: 'SKU Padre' },
            { input: ticketFilterInput, name: 'Ticket' },
            { input: lineamientoFilterInput, name: 'Lineamiento' }
        ];
        
        // Limpiar campos de forma eficiente
        fieldsToClean.forEach(field => {
            if (field.input && field.input.value !== '') {
                field.input.value = '';
                fieldsCleared++;
            }
        });
        
        // Limpiar indicadores visuales también
        clearAllFilterInputPending();
        
        // Log optimizado - solo una entrada con resumen
        if (fieldsCleared > 0) {
            const endTime = performance.now();
            logToBrowserConsole(`Limpieza de filtros: ${fieldsCleared} campos limpiados en ${(endTime - startTime).toFixed(2)}ms`, 'debug');
        } else {
            logToBrowserConsole('Limpieza de filtros: ningún campo necesitaba limpieza', 'debug');
        }
        
        // Limpiar checkboxes
        if (extendSkuHijoCheckbox) {
            extendSkuHijoCheckbox.checked = false;
        }

        logToBrowserConsole('Todos los filtros manuales han sido limpiados', 'info');
    }

    function isCurrentSourceSharePoint() {
        // Verificar si la fuente actual es de SharePoint
        if (!blobSelect || !blobSelect.value) {
            return false;
        }
        
        const currentBlobName = blobSelect.value;
        
        // SOLUCION SIMPLE: Lista hardcodeada de fuentes SharePoint conocidas
        // Basada en la configuración del backend
        const knownSharePointSources = [
            'UNIVERSO PERU',
            'DISEÑO PERU', 
            'REDACCION PERU',
            'INFO MARCA PROPIA PERU',
            'PERU ESTUDIO CHILE'
        ];
        
        const isSharePoint = knownSharePointSources.includes(currentBlobName);
        logToBrowserConsole(`isCurrentSourceSharePoint: ${currentBlobName} -> ${isSharePoint}`, 'info');
        return isSharePoint;
    }

    async function handleCacheVerification() {
        const { currentBlobDisplayName } = getState();
        
        if (!currentBlobDisplayName) {
            alert('Por favor selecciona una base de datos primero.');
            return;
        }

        // Mostrar modal y estado de carga
        verificationDatabaseName.textContent = currentBlobDisplayName;
        verificationLoading.style.display = 'block';
        verificationResult.style.display = 'none';
        verificationError.style.display = 'none';
        cacheVerificationModal.show();

        try {
            const response = await fetch(`${API_BASE}/api/data/check-updates/${encodeURIComponent(currentBlobDisplayName)}`);
            
            if (!response.ok) {
                throw new Error(`Error del servidor: ${response.status}`);
            }

            const result = await response.json();
            
            // Ocultar loading
            verificationLoading.style.display = 'none';
            
            if (result.check_error) {
                // Mostrar error
                verificationError.style.display = 'block';
                verificationErrorMessage.textContent = result.check_error;
            } else if (!result.cacheable) {
                // No cacheable
                verificationError.style.display = 'block';
                verificationErrorMessage.textContent = result.message || 'Esta base de datos no utiliza cache persistente.';
            } else {
                // Mostrar resultado
                verificationResult.style.display = 'block';
                
                // Configurar alerta según resultado
                if (result.update_available) {
                    verificationAlert.className = 'alert alert-warning';
                    verificationIcon.className = 'bi bi-exclamation-triangle-fill me-2';
                    verificationTitle.textContent = 'Actualización Disponible';
                    verificationMessage.textContent = result.recommendation || 'Se recomienda realizar una Carga Completa para obtener la versión más reciente.';
                    fullLoadRecommendationBtn.style.display = 'inline-block';
                } else {
                    verificationAlert.className = 'alert alert-success';
                    verificationIcon.className = 'bi bi-check-circle-fill me-2';
                    verificationTitle.textContent = 'Cache Actualizado';
                    verificationMessage.textContent = 'Tu cache local está actualizado con la última versión de SharePoint.';
                    fullLoadRecommendationBtn.style.display = 'none';
                }
                
                // Mostrar detalles
                verificationDetails.textContent = result.comparison_details || '';
                cacheTimestamp.textContent = result.cache_timestamp ? new Date(result.cache_timestamp).toLocaleString() : 'No disponible';
                remoteTimestamp.textContent = result.remote_last_modified || 'No disponible';
                
                // NUEVO: Sincronizar estado de notificación después de verificación manual
                // Si el cache está actualizado, ocultar la notificación de actualización
                if (!result.update_available) {
                    hideUpdateNotification();
                    logToBrowserConsole(`Notificación de actualización ocultada después de verificación manual para '${currentBlobDisplayName}'`, 'debug');
                }
            }

        } catch (error) {
            console.error('Error verificando actualizaciones:', error);
            verificationLoading.style.display = 'none';
            verificationError.style.display = 'block';
            verificationErrorMessage.textContent = `Error de conexión: ${error.message}`;
        }
    }

    async function handleDataLoad() {
        // Mostrar card de verificación automática
        showCacheStatusCard('verifying');

        const { currentBlobDisplayName, currentBlobFilename, setAbortController } = getState();
        const selectedBlobName = blobSelect ? blobSelect.value : currentBlobDisplayName;

        if (!currentBlobDisplayName && !selectedBlobName) {
            alert('Por favor, selecciona una fuente de datos.');
            hideCacheStatusCard();
            return;
        }

        const targetBlobName = selectedBlobName || currentBlobDisplayName;

        // ⚡ OPTIMIZACIÓN: Verificar cache de vista antes de cualquier procesamiento
        if (dataSourceCache[targetBlobName] && viewStateCache[targetBlobName]) {
            logToBrowserConsole(`Restaurando vista desde cache para '${targetBlobName}' - ULTRA RÁPIDO ⚡`);
            
            if (restoreViewState(targetBlobName)) {
                // Vista restaurada exitosamente desde cache
                logToBrowserConsole(`Vista restaurada instantáneamente para '${targetBlobName}'`, 'success');
                return;
            } else {
                // Si falló la restauración, limpiar el cache corrupto y continuar normalmente
                clearViewStateCache(targetBlobName);
                logToBrowserConsole(`Cache de vista corrupto para '${targetBlobName}', procediendo con carga normal`, 'warn');
            }
        }

        // Guardar estado actual antes de cambiar (para el cache de vista)
        const previousBlobName = getState().currentBlobDisplayName;
        if (previousBlobName && previousBlobName !== targetBlobName) {
            saveViewState(previousBlobName);
        }

        // ⚡ OPTIMIZACIÓN: Cancelar filtros pendientes al cambiar de base
        cancelPendingFilterUpdates();

        // --- MEJORA CLAVE: Limpiar filtros manuales ANTES de cargar nuevos datos ---
        clearManualFilterInputs();
        // --- FIN DE LA MEJORA ---

        // Limpiar la UI de la tabla antes de empezar la carga
        clearDataTable();

    const existingController = getState().abortController;
        if (existingController) {
            try {
                existingController.abort();
            } catch (error) {
                console.warn('Error al abortar controlador anterior:', error);
            }
        }

    const controller = new AbortController();
    setAbortController(controller);

    // Definir si es una base grande ANTES de usarla
    const isLargeBase = ['UNIVERSO CHILE', 'PERU_Staff', 'Peru_Diseno', 'Peru_Redaccion'].includes(currentBlobDisplayName);

    // Mensaje específico para bases grandes
    let loadingMessage = `Cargando datos para ${currentBlobDisplayName}...`;
    let submessage = 'Este proceso puede tomar unos momentos';
    
    if (isLargeBase) {
        loadingMessage = `Cargando base grande '${currentBlobDisplayName}'...`;
        submessage = '⚠️ Base grande: puede tardar desde minutos hasta 30+ minutos en equipos lentos. Usa el botón "Cancelar" solo si necesitas parar el proceso.';
    } else if (currentBlobDisplayName && (currentBlobDisplayName.includes('PERU') || currentBlobDisplayName.includes('DISEÑO') || currentBlobDisplayName.includes('REDACCION'))) {
        submessage = '📁 Cargando desde SharePoint. Tiempo variable según conexión y tamaño de datos.';
    } else {
        submessage = 'Tiempo de carga variable según el tamaño de los datos y velocidad del equipo.';
    }

    setState({
        isLoading: true,
        statusMessage: loadingMessage,
        loadingDetails: {
            message: `Cargando ${currentBlobDisplayName}`,
            submessage: submessage,
            isProcessing: true
        }
    });

    // Cerrar conexión SSE anterior si existe para evitar que añada cards viejas
    if (progressEventSource) {
        progressEventSource.close();
        progressEventSource = null;
        logToBrowserConsole('Conexión SSE anterior cerrada antes de nueva carga', 'debug');
    }

    // Limpiar cards anteriores y mostrar overlay moderno
    clearEventCards();
    toggleLoadingOverlay(true, loadingMessage, submessage, 0);

    // Actualizar título del overlay
    const loadingTitle = document.getElementById('loading-title');
    if (loadingTitle) {
        loadingTitle.textContent = `Cargando ${currentBlobDisplayName}`;
    }

    // Conectar al SSE de progreso real del backend
    let lastProgressUpdate = Date.now();

    try {
        progressEventSource = new EventSource(`${API_BASE}/api/progress/load/stream`);

        progressEventSource.onmessage = (event) => {
            try {
                const data = event.data.trim();
                if (data && data !== 'keep-alive') {
                    const progressData = JSON.parse(data);
                    lastProgressUpdate = Date.now();
                    handleProgressEvent(progressData);
                }
            } catch (error) {
                console.error('Error procesando mensaje SSE de progreso:', error);
            }
        };

        progressEventSource.onerror = (error) => {
            console.error('Error en SSE de progreso:', error);
            // No cerrar inmediatamente - el navegador reintenta automáticamente
        };

        logToBrowserConsole('Conectado al SSE de progreso de carga', 'info');

    } catch (error) {
        console.error('No se pudo conectar al SSE de progreso, usando fallback:', error);
        // Si falla la conexión SSE, continuar sin progreso real
        addEventCard('processing', 'Procesando datos...');
    }

    try {
        // Primero cargamos la configuración
        const settingsResponse = await fetchWithRetry(`${API_BASE}/api/config/settings/${currentBlobDisplayName}`, { 
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                },
                timeout: 60000  // 60s para dar tiempo a autenticación SharePoint
        }, 2, 1500);
        
        if (!settingsResponse.ok) {
            throw new Error(`Error al cargar configuración: ${settingsResponse.status}`);
        }
        
        const blobSettings = await settingsResponse.json();
        if (!blobSettings) {
            throw new Error('No se pudo obtener la configuración del servidor');
        }

        setState({ 
            hiddenColumnsConfig: Array.isArray(blobSettings.hide_columns) ? 
                blobSettings.hide_columns.map(c => String(c).toLowerCase()) : 
                []
        });

        // Luego cargamos los datos (siempre con verificación inteligente)
        const endpointUrl = `${API_BASE}/api/data/load/${currentBlobDisplayName}`;

        // Sin timeout fijo - dejar que el usuario decida cuándo cancelar
        // Para equipos lentos, algunos procesos pueden tardar 30+ minutos
        const loadResponse = await fetchWithRetry(endpointUrl, { 
            method: 'POST', 
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache'
            },
            timeout: null // Sin timeout automático
        }, 0); // Sin reintentos automáticos para evitar duplicar cargas largas

        if (!loadResponse.ok) {
            throw new Error(`Error al cargar datos: ${loadResponse.status}`);
        }

        const dataPayload = await loadResponse.json();
        if (!dataPayload) {
            throw new Error('No se recibieron datos del servidor');
        }

        // Mostrar card de estado según el resultado del caché inteligente
        const cacheDecision = dataPayload.cache_decision || 'no_cache';
        showCacheStatusCard(cacheDecision);

        // Log detallado según el tipo de carga
        if (cacheDecision === 'using_cache') {
            logToBrowserConsole(`✅ Datos cargados desde caché local (verificado como actualizado)`, 'success');
        } else if (cacheDecision === 'downloading_fresh') {
            logToBrowserConsole(`🔄 Nueva versión detectada - datos descargados desde servidor`, 'info');
        } else {
            logToBrowserConsole(`📦 Datos descargados desde servidor`, 'info');
        }

        // Validamos que tengamos las propiedades necesarias
        if (!Array.isArray(dataPayload.columns)) {
            throw new Error('El formato de datos recibido es inválido (columns)');
        }

        // Crear entrada en caché con validaciones
        dataSourceCache[currentBlobDisplayName] = {
            fileInfo: {
                displayName: currentBlobDisplayName,
                fileName: currentBlobFilename,
                columns: dataPayload.columns.map(c => String(c).toLowerCase()),
                rowCount: parseInt(dataPayload.row_count_original || 0, 10),
                cache_ttl_seconds: parseInt(dataPayload.cache_ttl_seconds || 300, 10)
            },
            filterOptions: dataPayload.filter_options || {},
            filterConfig: Array.isArray(blobSettings.filter_columns) ? 
                blobSettings.filter_columns.map(c => c.toLowerCase()) : 
                [],
            ttl: parseInt(dataPayload.cache_ttl_seconds || 300, 10),
            displayData: [],
            filteredRowCount: 0,
            valueFilters: {},
            selectedColumns: [],
            currentPage: 1,
            // Inicializar campos de prioridad
            hasPriorityColumn: false,
            priorityInfo: {}
        };

        // MEJORA: Actualizar indicadores de cache en el selector
        updateCacheIndicators();

        // Cerrar conexión SSE de progreso
        if (progressEventSource) {
            progressEventSource.close();
            progressEventSource = null;
            logToBrowserConsole('Conexión SSE de progreso cerrada', 'debug');
        }

        // Dar tiempo para que el usuario vea la última card antes de cerrar overlay
        setTimeout(() => {
            clearEventCards();
        }, 1500);

        logToBrowserConsole(`'${currentBlobDisplayName}' cargado y guardado en la caché del frontend.`);
            
            // Loaded bases panel removed - cache status shown in selector
        
        // Aplicar filtros iniciales
        await handleApplyFilters(1, true);
        
        // Actualizar disponibilidad de botones después de cargar datos
        updateButtonAvailability();

        // ⚡ OPTIMIZACIÓN: Guardar estado de vista después de carga exitosa
        setTimeout(() => {
            saveViewState(targetBlobName);
            logToBrowserConsole(`Estado de vista guardado para futuros accesos rápidos de '${targetBlobName}'`, 'debug');
        }, 500); // Delay más largo para asegurar que la UI esté completamente renderizada

        // 🔄 SINCRONIZACIÓN: Refrescar verificación automática después de carga completa exitosa
        setTimeout(() => {
            checkPersistentCacheAvailability(targetBlobName);
            // NUEVO: Sincronizar también el estado de notificación de actualización
            checkForUpdates(targetBlobName);
            logToBrowserConsole(`Verificación automática y notificación sincronizadas después de carga completa de '${targetBlobName}'`, 'debug');
        }, 1500); // Dar tiempo suficiente para que se actualice la metadata del cache persistente

        // Marcar como completado después de que todo termine exitosamente
        setState({ 
            isLoading: false,
            loadingDetails: {
                message: 'Carga completada exitosamente',
                submessage: '',
                isProcessing: false
            }
        });

    } catch (error) {
        // Cerrar conexión SSE de progreso en caso de error
        if (progressEventSource) {
            progressEventSource.close();
            progressEventSource = null;
        }

        // Limpiar cards en caso de error
        clearEventCards();

        console.error('Error en handleDataLoad:', error);
        
            // Verificar si el error es por cancelación manual del usuario
            if (error.name === 'AbortError') {
                console.log('Carga de datos cancelada por el usuario');
                setState({ 
                    statusMessage: 'Carga de datos cancelada.',
                    loadingDetails: {
                        message: 'Carga cancelada',
                        submessage: 'Proceso cancelado por el usuario',
                        isProcessing: false
                    }
                });
            } else {
        // Mejorar mensajes de error basados en el tipo de error
        let userMessage = 'Error al cargar datos';
        let detailedMessage = error.message;

        if (error.message && error.message.includes('ERR_CONNECTION_RESET')) {
            userMessage = 'Conexión Interrumpida';
            detailedMessage = 'El servidor cerró la conexión durante la operación. Intenta recargar la página.';
            showConnectivityWarning('connection_reset');
        } else if (error.message && error.message.includes('ERR_CONNECTION_REFUSED')) {
            userMessage = 'Servidor No Disponible';
            detailedMessage = 'El servidor de la aplicación no está corriendo. Verifica que el lanzador esté activo.';
            showConnectivityWarning('server_unavailable');
        } else if (error.message && error.message.includes('Failed to fetch')) {
            userMessage = 'Conexión Bloqueada';
            detailedMessage = 'Posible bloqueo por firewall o antivirus. Verifica la configuración de seguridad.';
            showConnectivityWarning('firewall_blocked');
        } else if (error.message && error.message.includes('HTTP 503')) {
            userMessage = 'Servicio No Disponible';
            detailedMessage = 'El servidor está temporalmente no disponible. Intenta nuevamente en unos momentos.';
            showConnectivityWarning('server_unavailable');
        } else if (error.message && error.message.includes('HTTP 50')) {
            userMessage = 'Error del Servidor';
            detailedMessage = 'Error interno del servidor. Contacta soporte técnico con detalles del error.';
            showConnectivityWarning('server_error');
        }
        
        setState({ 
            statusMessage: `${userMessage}: ${detailedMessage}`,
            loadingDetails: {
                message: userMessage,
                submessage: detailedMessage,
                isProcessing: false
            }
        });
        // Limpiar la caché si hubo un error
        if (dataSourceCache[currentBlobDisplayName]) {
            delete dataSourceCache[currentBlobDisplayName];
        }
        // Actualizar disponibilidad de botones después de error
        updateButtonAvailability();
            }
    } finally {
        setState({ 
            isLoading: false,
            loadingDetails: {
                message: '',
                submessage: '',
                isProcessing: false
            }
        });
            
            // Limpiar el controlador de aborto de forma segura
            try {
        setAbortController(null);
            } catch (error) {
                console.warn('Error al limpiar abort controller:', error);
            }
            
        // Actualizar disponibilidad de botones al finalizar
        updateButtonAvailability();
    }
}

// ===== FUNCIONES DE MODALES PARA RESULTADOS NO ENCONTRADOS =====

function mostrarModalResultadoVacio(totalBuscados, detalle) {
    const modal = new bootstrap.Modal(document.getElementById('emptyResultsModal'));
    document.getElementById('empty-total-buscados').textContent = totalBuscados;

    // Mostrar desglose por tipo de filtro
    let desglose = '';
    if (detalle.skusHijo.length > 0) desglose += `SKU Hijo: ${detalle.skusHijo.length}<br>`;
    if (detalle.skusPadre.length > 0) desglose += `SKU Padre: ${detalle.skusPadre.length}<br>`;
    if (detalle.tickets.length > 0) desglose += `Requerimientos: ${detalle.tickets.length}<br>`;
    if (detalle.lineamientos.length > 0) desglose += `Tickets: ${detalle.lineamientos.length}`;

    const detalleElement = document.getElementById('empty-detalle-busqueda');
    if (detalleElement) {
        detalleElement.innerHTML = desglose || 'No se especificó el tipo';
    }

    modal.show();
    logToBrowserConsole(`Modal de resultado vacío mostrado: ${totalBuscados} valores buscados, 0 encontrados`, 'info');
}

function mostrarModalResultadoParcial(totalBuscados, totalEncontrados, totalNoEncontrados, detalle) {
    const modal = new bootstrap.Modal(document.getElementById('partialResultsModal'));
    document.getElementById('partial-total-buscados').textContent = totalBuscados;
    document.getElementById('partial-total-encontrados').textContent = totalEncontrados;
    document.getElementById('partial-total-no-encontrados').textContent = totalNoEncontrados;

    // Mostrar desglose por tipo de filtro
    let desglose = '';
    if (detalle.skusHijo.length > 0) desglose += `SKU Hijo: ${detalle.skusHijo.length}<br>`;
    if (detalle.skusPadre.length > 0) desglose += `SKU Padre: ${detalle.skusPadre.length}<br>`;
    if (detalle.tickets.length > 0) desglose += `Requerimientos: ${detalle.tickets.length}<br>`;
    if (detalle.lineamientos.length > 0) desglose += `Tickets: ${detalle.lineamientos.length}`;

    const detalleElement = document.getElementById('partial-detalle-no-encontrados');
    if (detalleElement) {
        detalleElement.innerHTML = desglose || 'No hay desglose disponible';
    }

    // Guardar el detalle globalmente para la descarga
    window.detalleNoEncontradosGlobal = detalle;

    modal.show();
    logToBrowserConsole(`Modal de resultado parcial mostrado: ${totalBuscados} buscados, ${totalEncontrados} encontrados, ${totalNoEncontrados} no encontrados`, 'info');
}

// ===== FIN FUNCIONES DE MODALES =====

async function handleApplyFilters(page = 1, isInitialLoad = false) {
    const sourceName = getState().currentBlobDisplayName;
    if (!sourceName || !dataSourceCache[sourceName]) return;

    // Si es una carga inicial, reseteamos la UI de filtros y columnas
    if (isInitialLoad) {
        const cachedData = dataSourceCache[sourceName];
        populateFilterControls(cachedData.filterOptions, cachedData.filterConfig);
        populateColumnsListbox(cachedData.fileInfo.columns, getState().hiddenColumnsConfig);

        // Actualizar visibilidad de filtros según configuración de la base
        await updateFilterVisibility(sourceName);
    }

    currentPage = page;

    // ===== VALIDACIÓN DE PROCESAMIENTO POR LOTES =====
    // Verificar si se requiere procesamiento por lotes antes de continuar
    try {
        const batchValidation = validateBatchFilters();

        if (!batchValidation.valid) {
            // Mostrar error de conflicto (ambos checkboxes activos con >500)
            alert(batchValidation.error);
            return;
        }

        if (batchValidation.needsBatching) {
            // Se requiere procesamiento por lotes
            console.log(`🚀 Procesamiento por lotes requerido: ${batchValidation.totalBatches} lotes`);
            await handleBatchProcessing(batchValidation);
            return; // No continuar con el flujo normal
        }
    } catch (error) {
        console.error('Error en validación de lotes:', error);
        alert(`Error: ${error.message}`);
        return;
    }
    // ===== FIN VALIDACIÓN DE PROCESAMIENTO POR LOTES =====

    setState({
        isLoading: true,
        statusMessage: isInitialLoad ? 'Preparando vista inicial...' : 'Aplicando filtros...',
        loadingDetails: {
            message: isInitialLoad ? 'Preparando vista inicial...' : 'Aplicando filtros...',
            submessage: 'Procesando datos y actualizando vista',
            isProcessing: true
        }
    });

    try {
        const payload = getFilterPayload();
        const response = await fetch(`${API_BASE}/api/data/filter`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        const result = await response.json();

        // --- MANEJO DE VALORES NO ENCONTRADOS CON MODALES ---
        const noEncontradosHijo = result.skus_no_encontrados_hijo || [];
        const noEncontradosPadre = result.skus_no_encontrados_padre || [];
        const ticketsNoEncontrados = result.tickets_no_encontrados || [];
        const lineamientosNoEncontrados = result.lineamientos_no_encontrados || [];

        // Consolidar todos los valores no encontrados
        skusNoEncontrados = [...noEncontradosHijo, ...noEncontradosPadre];
        const totalNoEncontrados = skusNoEncontrados.length + ticketsNoEncontrados.length + lineamientosNoEncontrados.length;

        // Debug: Log de valores recibidos
        logToBrowserConsole(`🔍 DEBUG - skus_no_encontrados_hijo: ${noEncontradosHijo.length}`, 'info');
        logToBrowserConsole(`🔍 DEBUG - skus_no_encontrados_padre: ${noEncontradosPadre.length}`, 'info');
        logToBrowserConsole(`🔍 DEBUG - tickets_no_encontrados: ${ticketsNoEncontrados.length}`, 'info');
        logToBrowserConsole(`🔍 DEBUG - lineamientos_no_encontrados: ${lineamientosNoEncontrados.length}`, 'info');
        logToBrowserConsole(`🔍 DEBUG - total no encontrados: ${totalNoEncontrados}`, 'info');
        logToBrowserConsole(`🔍 DEBUG - result.row_count_filtered: ${result.row_count_filtered}`, 'info');

        if (totalNoEncontrados > 0) {
            // Usar row_count_filtered que es el total de filas encontradas, no solo la página actual
            const totalEncontrados = result.row_count_filtered || 0;
            const totalBuscados = totalNoEncontrados + totalEncontrados;

            logToBrowserConsole(`🔍 DEBUG - totalEncontrados (usando row_count_filtered): ${totalEncontrados}`, 'info');
            logToBrowserConsole(`🔍 DEBUG - totalBuscados: ${totalBuscados}`, 'info');

            // Crear objeto con el detalle de no encontrados
            const detalleNoEncontrados = {
                skusHijo: noEncontradosHijo,
                skusPadre: noEncontradosPadre,
                tickets: ticketsNoEncontrados,
                lineamientos: lineamientosNoEncontrados
            };

            if (totalEncontrados === 0) {
                // Caso A: No se encontró ningún valor
                logToBrowserConsole(`🔍 Mostrando modal de resultado vacío`, 'info');
                mostrarModalResultadoVacio(totalBuscados, detalleNoEncontrados);
            } else {
                // Caso B: Resultado parcial
                logToBrowserConsole(`🔍 Mostrando modal de resultado parcial`, 'info');
                mostrarModalResultadoParcial(totalBuscados, totalEncontrados, totalNoEncontrados, detalleNoEncontrados);
            }
        }
        // --- FIN MANEJO VALORES NO ENCONTRADOS ---
        
        // Almacenar información de prioridad si está disponible
        if (result.priority_info) {
            currentPriorityInfo = result.priority_info;
            logToBrowserConsole(`🔍 Información de prioridad recibida del backend:`, 'info');
            logToBrowserConsole(`   - has_priority_column: ${result.priority_info.has_priority_column}`, 'info');
            logToBrowserConsole(`   - column_name: ${result.priority_info.column_name}`, 'info');
            logToBrowserConsole(`   - priority_counts: ${JSON.stringify(result.priority_info.priority_counts)}`, 'info');
            logToBrowserConsole(`   - row_priorities keys: ${Object.keys(result.priority_info.row_priorities || {}).length}`, 'info');
        } else {
            currentPriorityInfo = {};
            logToBrowserConsole('❌ No se recibió información de prioridad del backend', 'debug');
        }

        // Actualizar el estado global
        getState().setDisplayData(result.data || [], result.row_count_filtered || 0);
        
        // Actualizar la caché
        const cacheEntry = dataSourceCache[sourceName];
        if (cacheEntry) {
            cacheEntry.displayData = result.data || [];
            cacheEntry.filteredRowCount = result.row_count_filtered || 0;
            cacheEntry.valueFilters = payload.value_filters;
            cacheEntry.selectedColumns = payload.selected_display_columns;
            cacheEntry.currentPage = currentPage;
            // Almacenar información de prioridad en caché para uso dinámico
            cacheEntry.hasPriorityColumn = result.has_priority_column || false;
            cacheEntry.priorityInfo = currentPriorityInfo;
        }

        // Renderizar UI
        renderDataTable(result.data || [], result.columns_in_data || []);
        renderPagination(result.row_count_filtered || 0);
        
        // Actualizar porcentajes si hay información de prioridad (siempre que haya datos, independientemente del toggle)
        if (result.priority_info && result.priority_info.has_priority_column) {
            logToBrowserConsole('🔧 Actualizando porcentajes después de recibir datos con información de prioridad', 'debug');
            updatePriorityPercentages();
        }

        // Actualizar elementos de UI adicionales
        const dataPayload = dataSourceCache[sourceName];

        // ⚡ OPTIMIZACIÓN: Limpiar indicadores visuales después de aplicar filtros exitosamente
        clearAllFilterInputPending();
        logToBrowserConsole('Filtros aplicados exitosamente - indicadores visuales limpiados', 'debug');
        
        // Habilitar/deshabilitar el toggle de prioridad basado en si hay columna de prioridad
        if (priorityColoringToggle) {
            if (result.has_priority_column) {
                priorityColoringToggle.disabled = false;
                const columnName = currentPriorityInfo && currentPriorityInfo.column_name ? currentPriorityInfo.column_name : 'detectada';
                logToBrowserConsole(`Toggle de prioridad habilitado - columna ${columnName} encontrada`, 'info');
            } else {
                priorityColoringToggle.disabled = true;
                priorityColoringToggle.checked = false;
                logToBrowserConsole('Toggle de prioridad deshabilitado - no se encontró columna de prioridad', 'info');
            }
            // Actualizar visibilidad de la leyenda
            updatePriorityLegendVisibility();
        }

    } catch (error) {
        console.error('Error al aplicar filtros:', error);
        setState({ 
            statusMessage: `Error al aplicar filtros: ${error.message}`,
            loadingDetails: {
                message: 'Error al aplicar filtros',
                submessage: error.message,
                isProcessing: false
            }
        });
    } finally {
        // Solo marcar como terminado si NO es una carga inicial
        // Las cargas iniciales son controladas por handleDataLoad
        if (!isInitialLoad) {
            setState({ 
                isLoading: false,
                loadingDetails: {
                    message: '',
                    submessage: '',
                    isProcessing: false
                }
            });
        }
    }
}

    // ========================================
    // FUNCIONES DE PROCESAMIENTO POR LOTES
    // ========================================

    // Variable global para controlar la cancelación del procesamiento por lotes
    let batchProcessCancelled = false;

    // Variable global para acumular SKUs no encontrados de todos los lotes
    let allBatchNotFoundSkus = {
        hijo: [],
        padre: []
    };

    /**
     * Valida que no haya conflictos con el procesamiento por lotes
     * (ambos checkboxes activos con >500 valores al mismo tiempo)
     */
    function validateBatchFilters() {
        const hijoText = skuHijoInput.value.trim();
        const padreText = skuPadreInput.value.trim();

        if (!hijoText && !padreText) {
            return { valid: true };
        }

        const hijoValues = hijoText ? hijoText.split(/[,;\s]+/).filter(Boolean) : [];
        const padreValues = padreText ? padreText.split(/[,;\s]+/).filter(Boolean) : [];

        const hijoBatchEnabled = batchProcessHijoCheckbox.checked;
        const padreBatchEnabled = batchProcessPadreCheckbox.checked;

        const hijoExceeds500 = hijoValues.length > 500;
        const padreExceeds500 = padreValues.length > 500;

        // Validar que no estén ambos checkboxes activos con >500 valores
        if (hijoBatchEnabled && padreBatchEnabled && hijoExceeds500 && padreExceeds500) {
            return {
                valid: false,
                error: 'No puedes procesar por lotes ambos filtros (SKU Hijo y SKU Padre) simultáneamente. Por favor, desactiva uno de los checkboxes de "Procesar por lotes".'
            };
        }

        // Determinar cuál filtro necesita procesamiento por lotes
        let batchType = null;
        let batchValues = [];

        if (hijoBatchEnabled && hijoExceeds500) {
            batchType = 'hijo';
            batchValues = hijoValues;
        } else if (padreBatchEnabled && padreExceeds500) {
            batchType = 'padre';
            batchValues = padreValues;
        }

        return {
            valid: true,
            needsBatching: batchType !== null,
            batchType: batchType,
            batchValues: batchValues,
            totalBatches: batchValues.length > 0 ? Math.ceil(batchValues.length / 500) : 0
        };
    }

    /**
     * Actualiza el modal con información del lote actual
     */
    function updateBatchModal(currentBatch, totalBatches, status = 'processing', notFoundCount = 0) {
        batchCurrentSpan.textContent = currentBatch;
        batchTotalSpan.textContent = totalBatches;

        const percentage = Math.round((currentBatch / totalBatches) * 100);
        batchProgressBar.style.width = `${percentage}%`;
        batchProgressBar.setAttribute('aria-valuenow', percentage);
        batchProgressText.textContent = `${percentage}%`;

        // Ocultar todos los estados primero
        batchSpinner.style.display = 'none';
        batchInfoAlert.classList.add('d-none');
        batchReadyAlert.classList.add('d-none');
        batchDownloadBtn.classList.add('d-none');
        batchCompletedSection.classList.add('d-none');
        batchNotfoundAlert.classList.add('d-none');
        batchDownloadNotfoundBtn.classList.add('d-none');
        batchCloseBtn.classList.add('d-none');
        batchCancelBtn.classList.remove('d-none');
        batchStatusTitle.classList.remove('d-none');

        if (status === 'processing') {
            batchSpinner.style.display = 'block';
            batchInfoAlert.classList.remove('d-none');
            batchInfoText.textContent = `Filtrando valores del lote ${currentBatch}...`;
        } else if (status === 'ready') {
            batchReadyAlert.classList.remove('d-none');
            batchDownloadBtn.classList.remove('d-none');
        } else if (status === 'completed') {
            // Ocultar elementos de progreso
            batchStatusTitle.classList.add('d-none');
            batchCancelBtn.classList.add('d-none');

            // Mostrar sección completada
            batchCompletedSection.classList.remove('d-none');
            batchCompletedSummary.textContent = `Se procesaron ${totalBatches} lotes exitosamente.`;
            batchCloseBtn.classList.remove('d-none');

            // Mostrar alerta de no encontrados si hay
            if (notFoundCount > 0) {
                batchNotfoundAlert.classList.remove('d-none');
                batchNotfoundCount.textContent = notFoundCount;
                batchDownloadNotfoundBtn.classList.remove('d-none');
            }
        }
    }

    /**
     * Genera y descarga un archivo TXT con los SKUs no encontrados
     */
    function generateNotFoundTxt() {
        const totalHijo = allBatchNotFoundSkus.hijo.length;
        const totalPadre = allBatchNotFoundSkus.padre.length;
        const total = totalHijo + totalPadre;

        if (total === 0) {
            console.log('No hay SKUs no encontrados para descargar');
            return;
        }

        // Generar contenido del TXT
        const timestamp = new Date().toLocaleString('es-CL');
        let content = `=== REPORTE DE SKUs NO ENCONTRADOS ===\n`;
        content += `Fecha de generación: ${timestamp}\n`;
        content += `Total de valores no encontrados: ${total}\n`;
        content += `\n`;

        if (totalHijo > 0) {
            content += `--- SKUs Hijo No Encontrados (${totalHijo}) ---\n`;
            allBatchNotFoundSkus.hijo.forEach(sku => {
                content += `${sku}\n`;
            });
            content += `\n`;
        }

        if (totalPadre > 0) {
            content += `--- SKUs Padre No Encontrados (${totalPadre}) ---\n`;
            allBatchNotFoundSkus.padre.forEach(sku => {
                content += `${sku}\n`;
            });
            content += `\n`;
        }

        content += `=== FIN DEL REPORTE ===\n`;

        // Crear y descargar el archivo
        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `skus_no_encontrados_${new Date().getTime()}.txt`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        console.log(`✅ Archivo TXT descargado con ${total} SKUs no encontrados`);
    }

    /**
     * Exporta un lote específico y descarga el Excel
     * También captura los SKUs no encontrados para el reporte final
     */
    async function exportBatch(batchPayload, batchNumber, totalBatches, batchType) {
        try {
            updateBatchModal(batchNumber, totalBatches, 'processing');

            // PASO 1: Primero llamar a /api/data/filter para obtener SKUs no encontrados
            const filterResponse = await fetch(`${API_BASE}/api/data/filter`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(batchPayload)
            });

            if (filterResponse.ok) {
                const filterResult = await filterResponse.json();

                // Capturar SKUs no encontrados de este lote
                const noEncontradosHijo = filterResult.skus_no_encontrados_hijo || [];
                const noEncontradosPadre = filterResult.skus_no_encontrados_padre || [];

                // Agregar a la lista acumulada (evitando duplicados)
                noEncontradosHijo.forEach(sku => {
                    if (!allBatchNotFoundSkus.hijo.includes(sku)) {
                        allBatchNotFoundSkus.hijo.push(sku);
                    }
                });
                noEncontradosPadre.forEach(sku => {
                    if (!allBatchNotFoundSkus.padre.includes(sku)) {
                        allBatchNotFoundSkus.padre.push(sku);
                    }
                });

                console.log(`Lote ${batchNumber}: ${noEncontradosHijo.length} hijo no encontrados, ${noEncontradosPadre.length} padre no encontrados`);
            }

            // PASO 2: Realizar la petición de exportación
            const response = await fetch(`${API_BASE}/api/data/export`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(batchPayload)
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
            }

            // Obtener el blob
            const blob = await response.blob();

            // Mostrar el modal como "listo" y esperar a que el usuario haga clic
            updateBatchModal(batchNumber, totalBatches, 'ready');

            // Retornar una promesa que se resuelve cuando el usuario hace clic en descargar
            return new Promise((resolve, reject) => {
                const downloadHandler = () => {
                    // Crear el enlace de descarga
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `reporte_lote${batchNumber}_${new Date().getTime()}.xlsx`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);

                    // Limpiar el event listener
                    batchDownloadBtn.removeEventListener('click', downloadHandler);
                    resolve();
                };

                // Agregar el event listener al botón de descarga
                batchDownloadBtn.addEventListener('click', downloadHandler);
            });

        } catch (error) {
            console.error(`Error en lote ${batchNumber}:`, error);
            throw error;
        }
    }

    /**
     * Orquesta el procesamiento por lotes completo
     */
    async function handleBatchProcessing(validation) {
        const { batchType, batchValues, totalBatches } = validation;

        console.log(`Iniciando procesamiento por lotes: ${totalBatches} lotes para ${batchValues.length} valores`);

        // Resetear flag de cancelación y lista de no encontrados
        batchProcessCancelled = false;
        allBatchNotFoundSkus = { hijo: [], padre: [] };

        // Mostrar el modal
        batchProcessModal.show();

        // Configurar el botón de cancelar
        const cancelHandler = () => {
            batchProcessCancelled = true;
            batchProcessModal.hide();
            console.log('⚠️ Procesamiento por lotes cancelado por el usuario');
        };
        batchCancelBtn.addEventListener('click', cancelHandler);

        // Configurar el botón de descarga de no encontrados
        const downloadNotFoundHandler = () => {
            generateNotFoundTxt();
        };
        batchDownloadNotfoundBtn.addEventListener('click', downloadNotFoundHandler);

        try {
            // Dividir en lotes de 500
            const batches = [];
            for (let i = 0; i < batchValues.length; i += 500) {
                batches.push(batchValues.slice(i, i + 500));
            }

            // Procesar cada lote secuencialmente
            for (let i = 0; i < batches.length; i++) {
                // Verificar si se canceló
                if (batchProcessCancelled) {
                    console.log('Procesamiento cancelado por el usuario');
                    break;
                }

                const batch = batches[i];
                const batchNumber = i + 1;

                console.log(`Procesando lote ${batchNumber}/${totalBatches} con ${batch.length} valores`);

                // Obtener el payload base
                const basePayload = getFilterPayload();

                // Modificar el payload para este lote específico
                if (batchType === 'hijo') {
                    basePayload.sku_hijo_manual_list = batch;
                } else if (batchType === 'padre') {
                    basePayload.sku_padre_manual_list = batch;
                }

                // Exportar este lote (espera a que el usuario descargue)
                await exportBatch(basePayload, batchNumber, totalBatches, batchType);

                // Pequeño delay entre lotes (solo si no es el último)
                if (i < batches.length - 1 && !batchProcessCancelled) {
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
            }

            // Mostrar resumen final si no fue cancelado
            if (!batchProcessCancelled) {
                const totalNotFound = allBatchNotFoundSkus.hijo.length + allBatchNotFoundSkus.padre.length;
                console.log(`✅ Procesamiento completado: ${totalBatches} lotes, ${totalNotFound} SKUs no encontrados`);

                // Mostrar el modal con estado "completado"
                updateBatchModal(totalBatches, totalBatches, 'completed', totalNotFound);
                // El modal se cerrará cuando el usuario haga clic en "Cerrar"
            } else {
                // Si fue cancelado, cerrar el modal
                batchProcessModal.hide();
            }

        } catch (error) {
            console.error('Error en procesamiento por lotes:', error);
            batchProcessModal.hide();
            console.error(`❌ Error en procesamiento por lotes: ${error.message}`);
            alert(`Error en procesamiento por lotes: ${error.message}`);
        } finally {
            // Limpiar los event listeners
            batchCancelBtn.removeEventListener('click', cancelHandler);
            batchDownloadNotfoundBtn.removeEventListener('click', downloadNotFoundHandler);
        }
    }

    // ========================================
    // FIN FUNCIONES DE PROCESAMIENTO POR LOTES
    // ========================================

    function getFilterPayload() {
        const state = getState();
        const valueFiltersPayload = {};

        // Recolectar valores de los selects (ahora todos son de selección múltiple)
        filterControlsContainer.querySelectorAll('select.filter-select').forEach(select => {
            const colName = select.dataset.column;
            const selectedOptions = Array.from(select.selectedOptions).map(opt => opt.value);
            if (selectedOptions.length > 0) {
                valueFiltersPayload[colName] = selectedOptions;
            }
        });

        const getListFromInput = (input, allowBatching = false) => {
            const text = input.value.trim();
            if (!text) {
                return null;
            }

            // Divide por comas, puntos y comas o cualquier espacio en blanco (incluidos saltos de línea y tabulaciones).
            // Esto permite pegar directamente desde columnas de Excel.
            let values = text.split(/[,;\s]+/).map(s => s.trim()).filter(Boolean);

            if (values.length > 500 && !allowBatching) {
                const originalCount = values.length;
                // En lugar de truncar, lanzamos un error para bloquear la aplicación de filtros
                throw new Error(`Te excediste de 500 SKU!, el límite son 500. Se detectaron ${originalCount} valores. Para procesar más de 500, activa la opción "Procesar por lotes (>500)".`);
            }

            return values.length > 0 ? values : null;
        };
        
        // Recopilar filtros personalizados de texto
        const customTextFilters = {};
        const customFilterInputs = document.querySelectorAll('.custom-text-filter-input');
        customFilterInputs.forEach(input => {
            const columnName = input.dataset.column;
            const values = getListFromInput(input);
            if (values && values.length > 0) {
                customTextFilters[columnName] = values;
            }
        });

        return {
            blob_filename: state.currentBlobFilename,
            value_filters: valueFiltersPayload,
            use_sku_hijo_file: state.skuHijoFileLoaded,
            extend_sku_hijo: extendSkuHijoCheckbox.checked,
            sku_hijo_manual_list: getListFromInput(skuHijoInput, batchProcessHijoCheckbox.checked),
            use_sku_padre_file: state.skuPadreFileLoaded,
            sku_padre_manual_list: getListFromInput(skuPadreInput, batchProcessPadreCheckbox.checked),
            ticket_manual_list: getListFromInput(ticketFilterInput),
            lineamiento_manual_list: getListFromInput(lineamientoFilterInput),
            selected_display_columns: currentSelectedDisplayColumns,
            enable_priority_coloring: priorityColoringToggle ? priorityColoringToggle.checked : false,
            page: currentPage,
            page_size: PAGE_SIZE,
            custom_text_filters: Object.keys(customTextFilters).length > 0 ? customTextFilters : null
        };
    }

    async function handleExport(format) {
        const { currentBlobDisplayName } = getState();
        if (!currentBlobDisplayName) {
            alert('No hay datos para exportar.');
            return;
        }

        const endpoint = format === 'excel' ? `${API_BASE}/api/data/export` : `${API_BASE}/api/data/export-csv`;
        const fileExtension = format === 'excel' ? 'xlsx' : 'csv';
        const friendlyName = format === 'excel' ? 'Excel' : 'CSV';

        // Configurar estado de exportación
        isExporting = true;
        currentExportAbortController = new AbortController();
        
        // Mostrar botón de cancelación y ocultar botones de exportación
        if (cancelExportButton) cancelExportButton.style.display = 'inline-block';
        if (exportExcelButton) exportExcelButton.style.display = 'none';
        if (exportCsvButton) exportCsvButton.style.display = 'none';

        setState({ isLoading: true, statusMessage: `Preparando exportación a ${friendlyName}...` });

        try {
            // Usamos getFilterPayload para obtener la configuración actual de filtros
            const requestBody = getFilterPayload();
            
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
                signal: currentExportAbortController.signal
            });

            if (!response.ok) {
                if (response.status === 499) {
                    throw new Error("Exportación cancelada por el usuario.");
                }
                throw new Error(`Error del servidor: ${response.statusText}`);
            }

            const blob = await response.blob();
            const filename = `Export_${currentBlobDisplayName.replace(/\s/g, '_')}_${new Date().toISOString().slice(0, 10)}.${fileExtension}`;
            
            // Crear un enlace temporal para descargar el archivo
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);
            
            setState({ statusMessage: `Exportación a ${friendlyName} completada.` });

        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Exportación cancelada por el usuario.');
                setState({ statusMessage: 'Exportación cancelada.' });
            } else {
                console.error(`Error en exportación a ${friendlyName}:`, error);
                setState({ statusMessage: `Error en exportación: ${error.message}` });
            }
        } finally {
            // Restaurar estado de botones
            isExporting = false;
            currentExportAbortController = null;
            
            if (cancelExportButton) cancelExportButton.style.display = 'none';
            if (exportExcelButton) exportExcelButton.style.display = 'inline-block';
            if (exportCsvButton) exportCsvButton.style.display = 'inline-block';
            
            setState({ isLoading: false });
        }
    }

    async function handleFileUpload(fileInput, apiUrl, statusElement, type) {
        const file = fileInput.files[0];
        if (!file) return;
        setState({ isLoading: true, statusMessage: `Subiendo ${type}...` });
        const formData = new FormData();
        formData.append('file', file);
        try {
            const response = await fetch(apiUrl, { method: 'POST', body: formData });
            if (!response.ok) throw new Error(`HTTP error ${response.status}`);
            const result = await response.json();
            if (type === 'SKU Hijo') setState({ skuHijoFileLoaded: (result.sku_count || 0) > 0 });
            else if (type === 'SKU Padre') setState({ skuPadreFileLoaded: (result.sku_count || 0) > 0 });
            if (statusElement) statusElement.textContent = result.message;
            await handleApplyFilters();
        } catch (error) {
            if (statusElement) statusElement.textContent = `Error: ${error.message}`;
            setState({ statusMessage: `Error en subida: ${error.message}` });
        } finally {
            setState({ isLoading: false });
            fileInput.value = '';
        }
    }

    async function handleFileClear(apiUrl, statusElement, type) {
        if (statusElement) statusElement.textContent = '';
        if (type === 'SKU Hijo') setState({ skuHijoFileLoaded: false });
        else if (type === 'SKU Padre') setState({ skuPadreFileLoaded: false });
        else if (type === 'Ticket') { /* Para futuro uso */ }

        try {
            // Notificar al backend que debe limpiar su estado
            await fetch(apiUrl, { method: 'DELETE' });
        } catch (error) {
            console.error(`Error en el backend al limpiar ${type}:`, error);
            setState({ statusMessage: `Error en el servidor al limpiar filtro.` });
        }
    }

    async function handleCancelExport() {
        if (!isExporting) return;

        try {
            // Cancelar la petición fetch en curso
            if (currentExportAbortController) {
                currentExportAbortController.abort();
            }

            // Notificar al backend que cancele la exportación
            await fetch(`${API_BASE}/api/data/export-cancel`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            setState({ statusMessage: 'Cancelando exportación...' });
        } catch (error) {
            console.error('Error al cancelar exportación:', error);
            setState({ statusMessage: 'Error al cancelar exportación.' });
        }
    }
    
    async function fetchBlobOptions() {
        setState({ isLoading: true, statusMessage: 'Cargando configuración...' });
        try {
            const response = await fetchWithRetry(`${API_BASE}/api/config/blobs`, {
                timeout: 10000
            }, 2, 1000);
            const config = await response.json();
            sourcesByCountry = config.sources_by_country || {};
            if (countrySelect) {
                countrySelect.innerHTML = '<option value="">Seleccione un país...</option>';
                (config.countries || []).forEach(country => {
                    countrySelect.add(new Option(country, country));
                });
            }
            if (blobSelect) blobSelect.innerHTML = '<option value="">--</option>';
            setState({ statusMessage: 'Listo.' });
        } catch (error) {
            setState({ statusMessage: `Error al cargar config: ${error.message}` });
        } finally {
            setState({ isLoading: false });
        }
    }

    function populateBlobSelect(selectedCountry) {
        blobSelect.innerHTML = '<option selected disabled value="">Seleccione una fuente...</option>';
        const sources = sourcesByCountry[selectedCountry] || [];
        sources.forEach(source => {
            const option = document.createElement('option');
            option.value = source.display_name;
            
            // MEJORA: Indicador visual para fuentes en cache
            const isInCache = dataSourceCache[source.display_name] !== undefined;
            const cacheIndicator = isInCache ? ' 📋' : '';
            option.textContent = source.display_name + cacheIndicator;
            
            // Guardamos el source_type para usarlo después
            logToBrowserConsole(`Creando option para ${source.display_name}: sourceType=${source.source_type}`, 'debug');
            option.dataset.sourceType = source.source_type;
            option.dataset.description = source.description;
            blobSelect.appendChild(option);
        });
        blobSelect.disabled = sources.length === 0;
        descriptionSection.style.display = 'none';
    }

    let logStreamRetryCount = 0;
    const MAX_LOG_STREAM_RETRIES = 3;
    const LOG_STREAM_RETRY_DELAY = 2000;

    function connectToLogStream() {
        if (logEventSource) {
            logEventSource.close();
        }
        
        logEventSource = new EventSource(`${API_BASE}/api/logs/stream`);
        
        logEventSource.onmessage = (event) => {
            logStreamRetryCount = 0; // Reset counter on successful connection
            if (consoleOutputDiv) {
                const logEntry = document.createElement('div');
                logEntry.className = 'log-entry';
                const logMessage = event.data;

                // Resaltar mensajes importantes con clases especiales
                if (logMessage.includes('⏳ Procesando archivo CSV grande')) {
                    logEntry.className = 'log-entry log-warning-large-file';
                    logEntry.style.backgroundColor = '#fff3cd';
                    logEntry.style.borderLeft = '4px solid #ffc107';
                    logEntry.style.padding = '8px';
                    logEntry.style.fontWeight = 'bold';
                } else if (logMessage.includes('⏱️  Tiempo estimado')) {
                    logEntry.className = 'log-entry log-info-estimate';
                    logEntry.style.backgroundColor = '#d1ecf1';
                    logEntry.style.borderLeft = '4px solid #0dcaf0';
                    logEntry.style.padding = '8px';
                    logEntry.style.fontStyle = 'italic';
                } else if (logMessage.includes('✅ Parsing CSV completado')) {
                    logEntry.className = 'log-entry log-success';
                    logEntry.style.backgroundColor = '#d1e7dd';
                    logEntry.style.borderLeft = '4px solid #28a745';
                    logEntry.style.padding = '8px';
                    logEntry.style.fontWeight = 'bold';
                } else if (logMessage.includes('Descarga SharePoint completada')) {
                    logEntry.className = 'log-entry log-info';
                    logEntry.style.backgroundColor = '#e7f3ff';
                    logEntry.style.borderLeft = '4px solid #0d6efd';
                    logEntry.style.padding = '8px';
                }

                logEntry.textContent = logMessage;
                consoleOutputDiv.appendChild(logEntry);
                consoleOutputDiv.scrollTop = consoleOutputDiv.scrollHeight;
            }
        };
        
        logEventSource.onerror = (error) => {
            logToBrowserConsole("Error en conexión de logs.", "error");
            if (logEventSource) {
                logEventSource.close();
                logEventSource = null;
            }
            
            // Retry mechanism for log stream
            if (logStreamRetryCount < MAX_LOG_STREAM_RETRIES) {
                logStreamRetryCount++;
                logToBrowserConsole(`Reintentando conexión de logs (${logStreamRetryCount}/${MAX_LOG_STREAM_RETRIES})...`, "info");
                setTimeout(() => {
                    connectToLogStream();
                }, LOG_STREAM_RETRY_DELAY * logStreamRetryCount); // Exponential backoff
            } else {
                logToBrowserConsole("Conexión de logs falló después de múltiples intentos. Revise su conectividad de red.", "error");
            }
        };
    }


    function setupEventListeners() {

        console.log("DEBUG 1: Configurando el listener de filtros. Si ves esto, el script se ejecuta.");


        if (filterControlsContainer) {
            filterControlsContainer.addEventListener('shown.bs.collapse', function (event) {
                console.log("DEBUG 2: ¡El filtro se ha expandido! Evento 'shown.bs.collapse' detectado.");

                const leftPanelBody = document.querySelector('#left-panel .card-body');

                if (leftPanelBody) {
                    console.log("DEBUG 3: Se encontró el panel izquierdo. Forzando el redibujado ahora.");
                    leftPanelBody.style.display = 'block';
                    leftPanelBody.offsetHeight;
                    leftPanelBody.style.display = '';
                } else {
                    console.error("DEBUG 4: ¡ERROR CRÍTICO! No se pudo encontrar el elemento '#left-panel .card-body'.");
                }
            });
        } else {
            console.error("DEBUG 5: ¡ERROR CRÍTICO! No se pudo encontrar el elemento 'filterControlsContainer'.");
        }

        if (filterControlsContainer) {
            filterControlsContainer.addEventListener('shown.bs.collapse', function () {
                const leftPanelBody = document.querySelector('#left-panel .card-body');
                if (leftPanelBody) {
                    // MÉTODO MÁS POTENTE: Alternar una clase para forzar el reflow.
                    leftPanelBody.classList.add('force-reflow');
                    leftPanelBody.offsetHeight; // Forzar recálculo de layout
                    leftPanelBody.classList.remove('force-reflow');
                }
            });
        }

        // Scroll con mejor manejo de errores
        if (topScroll && dataTableWrapper) {
        topScroll.addEventListener('scroll', () => {
                try {
            if (!isSyncingScroll) {
                isSyncingScroll = true;
                dataTableWrapper.scrollLeft = topScroll.scrollLeft;
                        isSyncingScroll = false;
                    }
                } catch (error) {
                    console.warn('Error en sincronización de scroll:', error);
                isSyncingScroll = false;
            }
        });
        }

        if (dataTableWrapper && topScroll) {
        dataTableWrapper.addEventListener('scroll', () => {
                try {
            if (!isSyncingScroll) {
                isSyncingScroll = true;
                topScroll.scrollLeft = dataTableWrapper.scrollLeft;
                        isSyncingScroll = false;
                    }
                } catch (error) {
                    console.warn('Error en sincronización de scroll:', error);
                isSyncingScroll = false;
            }
        });
        }

        // Actualizar scroll superior al cambiar tamaño de ventana
        window.addEventListener('resize', () => {
            setTimeout(() => manageDualScroll(), 100);
        });

        // Selects con mejor manejo de errores
        if (countrySelect) {
        countrySelect.addEventListener('change', function () {
                try {
            populateBlobSelect(this.value);
            
            logToBrowserConsole("País cambiado, limpiando la interfaz de usuario.");

            // Limpiar la tabla de datos y la paginación
            if (dataTableHead) dataTableHead.innerHTML = '';
            if (dataTableBody) dataTableBody.innerHTML = '<tr><td colspan="100" class="text-center text-muted p-3">Seleccione una fuente de datos.</td></tr>';
            if (paginationContainer) paginationContainer.innerHTML = '';

            // Limpiar los contenedores de filtros y columnas
            if (filterControlsContainer) filterControlsContainer.innerHTML = '<p class="text-muted small my-1">Seleccione una fuente de datos para ver los filtros.</p>';
            if (columnsListboxContainer) columnsListboxContainer.innerHTML = '<p class="text-muted small my-1">Seleccione una fuente de datos para ver las columnas.</p>';
            
            // Resetear el estado de la aplicación relacionado con los datos
            setState({
                currentBlobDisplayName: null,
                currentBlobFilename: null,
                rowCount: { original: 0, display: 0, filtered: 0 },
                statusMessage: 'Seleccione una fuente de datos.'
            });

            updateHeaderStyle(null);
                } catch (error) {
                    console.error('Error al cambiar país:', error);
                    logToBrowserConsole(`Error al cambiar país: ${error.message}`, 'error');
                }
        });
        }

        if (blobSelect) {
        blobSelect.addEventListener('change', async (e) => {
                try {
            const selectedOption = e.target.selectedOptions[0];
            const sourceType = selectedOption.dataset.sourceType;
            const description = selectedOption.dataset.description;
            const displayName = selectedOption.value;

            // CORRECCIÓN CRÍTICA: Limpiar completamente la UI al cambiar de fuente
            if (dataTableHead) dataTableHead.innerHTML = '';
            if (dataTableBody) {
                // Siempre usar el estado inteligente, no 'loading'
                setTableState('no-query', displayName);
            }
            if (paginationContainer) paginationContainer.innerHTML = '';
            if (rowCountMessage) rowCountMessage.textContent = '0';
            
            // Limpiar contadores
            if (rowCountMessage) {
                rowCountMessage.textContent = '0';
            }
            
            // Limpiar filtros de la UI
            if (filterControlsContainer) {
                filterControlsContainer.innerHTML = '';
            }
            
            // Limpiar columnas
            if (columnsListboxContainer) {
                columnsListboxContainer.innerHTML = '';
            }

            // --- NUEVA FUNCIONALIDAD: Limpiar campos de texto de filtros al cambiar de base ---
            // Esto evita que se apliquen automáticamente filtros irrelevantes para la nueva base
            logToBrowserConsole(`Limpiando campos de texto de filtros al cambiar a '${displayName}'`, 'info');
            
            // Limpiar campos de texto SKU y otros filtros
            if (skuHijoInput) {
                skuHijoInput.value = '';
                logToBrowserConsole('Campo SKU Hijo limpiado', 'debug');
            }
            if (skuPadreInput) {
                skuPadreInput.value = '';
                logToBrowserConsole('Campo SKU Padre limpiado', 'debug');
            }
            if (ticketFilterInput) {
                ticketFilterInput.value = '';
                logToBrowserConsole('Campo Ticket limpiado', 'debug');
            }
            if (lineamientoFilterInput) {
                lineamientoFilterInput.value = '';
                logToBrowserConsole('Campo Lineamiento limpiado', 'debug');
            }
            
            // Limpiar checkboxes y estados
            if (extendSkuHijoCheckbox) {
                extendSkuHijoCheckbox.checked = false;
            }
            
            // Limpiar estados de archivos cargados en el store
            setState({ 
                skuHijoFileLoaded: false, 
                skuPadreFileLoaded: false 
            });
            
            // Limpiar indicadores de estado de archivos
            if (skuHijoStatus) skuHijoStatus.textContent = '';
            if (skuPadreStatus) skuPadreStatus.textContent = '';
            if (ticketFileStatus) ticketFileStatus.textContent = '';
            
            logToBrowserConsole('Todos los campos de filtros han sido limpiados para la nueva base', 'info');

            // --- CORRECCIÓN CLAVE ---
            // Actualizamos el estado global con la fuente seleccionada.
            // Esto permitirá que updateButtonAvailability funcione correctamente.
            setState({
                currentBlobDisplayName: displayName,
                currentBlobFilename: displayName, // Temporal hasta cargar
                dataForDisplay: [],
                rowCount: { original: 0, filtered: 0, display: 0 }
            });

            // Actualizar visibilidad de opciones de cache según la base seleccionada
            updateCacheOptionsVisibility(displayName);

            // Actualizar visibilidad de filtros según configuración de la base
            await updateFilterVisibility(displayName);

            // CORRECCIÓN: Actualizar inmediatamente la disponibilidad de botones
            updateButtonAvailability();

            // Actualizar estado visual sin cargar datos automáticamente
            // MEJORA: También verificar cache persistente, no solo TTL en memoria
            if (dataSourceCache[displayName]) {
                logToBrowserConsole(`Fuente '${displayName}' seleccionada (con datos en cache TTL disponibles)`, 'info');
            } else {
                logToBrowserConsole(`Fuente '${displayName}' seleccionada (sin cache TTL)`, 'info');

                // Verificar cache persistente de forma asíncrona
                checkPersistentCacheAvailability(displayName);
            }

            // Mostrar/ocultar aviso de SharePoint
            const sharepointNotice = document.getElementById('sharepoint-auth-notice');
            if (sharepointNotice) {
                sharepointNotice.style.display = sourceType === 'sharepoint' ? 'block' : 'none';
            }
            
            if (description) {
                descriptionBox.textContent = description;
                descriptionSection.style.display = 'block';
            } else {
                descriptionSection.style.display = 'none';
            }
            updateHeaderStyle(displayName);
            
            // CORRECCIÓN: Segunda llamada para asegurar que todo esté sincronizado
            setTimeout(() => updateButtonAvailability(), 100);
            
            // NUEVA FUNCIONALIDAD: Verificar actualizaciones para cache persistente
            checkForUpdates(displayName);
                    
                    // Loaded bases panel removed - cache status shown in selector
                } catch (error) {
                    console.error('Error al cambiar fuente de datos:', error);
                    logToBrowserConsole(`Error al cambiar fuente de datos: ${error.message}`, 'error');
                }
            });
        }

        // Botón de carga simplificado con caché inteligente automático
        loadDataBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            await handleDataLoad();
        });

        applyFiltersButton.addEventListener('click', () => handleApplyFilters(1));

        exportExcelButton.addEventListener('click', () => handleExport('excel'));
        exportCsvButton.addEventListener('click', () => handleExport('csv'));
        cancelExportButton.addEventListener('click', handleCancelExport);

        clearAllFiltersButton.addEventListener('click', () => {
            // Solo limpiar los campos de filtros manuales (texto, archivos, selects)
            clearManualFilterInputs();
            // Opcional: limpiar selects de filtros de columnas si aplica
            if (filterControlsContainer) {
                filterControlsContainer.querySelectorAll('select').forEach(select => {
                    if (select.tomselect) {
                        select.tomselect.clear();
                    } else {
                        Array.from(select.options).forEach(option => option.selected = false);
                    }
                });
            }
            // No limpiar la tabla, ni los contadores, ni llamar al backend
            setState({ statusMessage: "Filtros limpiados. La tabla permanece igual." });
        });

        // ===== FUNCIONES AUXILIARES DE FAVORITOS =====

        /**
         * Abre el modal de favoritos en modo guardar o cargar
         * @param {string} mode - 'save' o 'load'
         */
        /**
         * Guarda el favorito con un solo clic (sin modal)
         */
        async function saveFavoriteHandler() {
            const { currentBlobDisplayName } = getState();

            // Validar que hay datos cargados
            if (!currentBlobDisplayName) {
                showContextMessage({
                    type: 'warning',
                    title: 'Sin datos',
                    message: 'Debes cargar una fuente de datos primero para guardar un favorito.'
                });
                return;
            }

            try {
                // Obtener filtros actuales
                const { value_filters } = getFilterPayload();

                // Construir estado a guardar
                const stateToSave = {
                    value_filters: value_filters,
                    selected_columns: currentSelectedDisplayColumns,
                    extend_sku_search: extendSkuHijoCheckbox ? extendSkuHijoCheckbox.checked : false
                };

                // Guardar favorito en el servidor para esta base específica
                const success = await FavoritesManager.saveFavorite(stateToSave, currentBlobDisplayName);

                if (success) {
                    showContextMessage({
                        type: 'success',
                        title: 'Favorito Guardado',
                        message: `Tu configuración ha sido guardada para <strong>${currentBlobDisplayName}</strong> y estará disponible cada vez que cargues esta base.`
                    });
                } else {
                    throw new Error('No se pudo guardar el favorito en el servidor');
                }

            } catch (error) {
                console.error('Error guardando favorito:', error);
                showContextMessage({
                    type: 'error',
                    title: 'Error',
                    message: error.message || 'Error al guardar el favorito'
                });
            }
        }

        /**
         * Carga el favorito guardado para la base de datos actual
         */
        async function loadFavoriteHandler() {
            const { currentBlobDisplayName } = getState();

            // Validar que hay datos cargados
            if (!currentBlobDisplayName) {
                showContextMessage({
                    type: 'warning',
                    title: 'Sin datos',
                    message: 'Debes cargar una fuente de datos primero para cargar un favorito.'
                });
                return;
            }

            try {
                // Obtener favorito del servidor para esta base específica
                const favorite = await FavoritesManager.loadFavorite(currentBlobDisplayName);

                if (!favorite) {
                    showContextMessage({
                        type: 'info',
                        title: 'Sin favorito',
                        message: `No hay ningún favorito guardado para <strong>${currentBlobDisplayName}</strong>. Guarda uno primero.`
                    });
                    return;
                }

                // Aplicar filtros de valores
                const valueFiltersToApply = favorite.value_filters || {};
                filterControlsContainer.querySelectorAll('select.filter-select').forEach(select => {
                    const colName = select.dataset.column;
                    Array.from(select.options).forEach(option => {
                        option.selected = (valueFiltersToApply[colName] || []).includes(option.value);
                    });
                });

                // Aplicar selección de columnas
                const savedSelectedCols = (favorite.selected_columns || []).map(c => String(c).toLowerCase());
                if (columnsListboxContainer && savedSelectedCols.length > 0) {
                    currentSelectedDisplayColumns = [];
                    columnsListboxContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                        const isChecked = savedSelectedCols.includes(cb.value);
                        cb.checked = isChecked;
                        if (isChecked) {
                            currentSelectedDisplayColumns.push(cb.value);
                        }
                    });
                }

                // Aplicar checkbox de extensión
                if (extendSkuHijoCheckbox) {
                    extendSkuHijoCheckbox.checked = favorite.extend_sku_search || false;
                }

                // Notificar éxito
                showContextMessage({
                    type: 'success',
                    title: 'Favorito Cargado',
                    message: `Tu configuración de <strong>${currentBlobDisplayName}</strong> ha sido cargada. Haz clic en "Aplicar Filtros" para ver los resultados.`
                });

            } catch (error) {
                console.error('Error cargando favorito:', error);
                showContextMessage({
                    type: 'error',
                    title: 'Error al Cargar',
                    message: error.message || 'No se pudo cargar el favorito'
                });
            }
        }


        // ===== FUNCIONES Y LÓGICA DE QUICK ACTIONS =====

        /**
         * Muestra el modal de Quick Actions si no hay datos cargados
         */
        function showQuickActionsIfNeeded() {
            // Verificar si ya hay datos cargados
            const { currentBlobDisplayName } = getState();

            // Solo mostrar si no hay datos cargados
            if (!currentBlobDisplayName || Object.keys(dataSourceCache).length === 0) {
                // Esperar un poco para que la página cargue completamente
                setTimeout(() => {
                    quickActionsModal.show();
                }, 1500);
            }
        }

        /**
         * Selecciona el primer país y la primera fuente disponible para Chile
         */
        async function selectChileQuickAction() {
            try {
                quickActionsModal.hide();

                // Buscar Chile en el selector de países
                const chileOption = Array.from(countrySelect.options).find(
                    opt => opt.value.toLowerCase() === 'chile' || opt.textContent.toLowerCase().includes('chile')
                );

                if (!chileOption) {
                    showContextMessage({
                        type: 'error',
                        title: 'Error',
                        message: 'No se encontró Chile en las opciones disponibles'
                    });
                    return;
                }

                // Seleccionar Chile
                countrySelect.value = chileOption.value;
                countrySelect.dispatchEvent(new Event('change'));

                // Esperar a que se actualicen las fuentes
                await new Promise(resolve => setTimeout(resolve, 300));

                // Seleccionar la primera fuente disponible de Chile
                if (blobSelect.options.length > 1) { // > 1 porque hay opción vacía
                    blobSelect.selectedIndex = 1; // Primera opción real
                    blobSelect.dispatchEvent(new Event('change'));

                    // Esperar y cargar datos
                    await new Promise(resolve => setTimeout(resolve, 200));
                    await handleDataLoad(); // Carga rápida
                } else {
                    showContextMessage({
                        type: 'warning',
                        title: 'Sin datos',
                        message: 'No hay fuentes de datos disponibles para Chile'
                    });
                }

            } catch (error) {
                console.error('Error en Quick Action Chile:', error);
                showContextMessage({
                    type: 'error',
                    title: 'Error',
                    message: 'No se pudo cargar los datos de Chile'
                });
            }
        }

        /**
         * Selecciona el primer país y la primera fuente disponible para Perú
         */
        async function selectPeruQuickAction() {
            try {
                quickActionsModal.hide();

                // Buscar Perú en el selector de países
                const peruOption = Array.from(countrySelect.options).find(
                    opt => opt.value.toLowerCase() === 'peru' ||
                           opt.value.toLowerCase() === 'perú' ||
                           opt.textContent.toLowerCase().includes('per')
                );

                if (!peruOption) {
                    showContextMessage({
                        type: 'error',
                        title: 'Error',
                        message: 'No se encontró Perú en las opciones disponibles'
                    });
                    return;
                }

                // Seleccionar Perú
                countrySelect.value = peruOption.value;
                countrySelect.dispatchEvent(new Event('change'));

                // Esperar a que se actualicen las fuentes
                await new Promise(resolve => setTimeout(resolve, 300));

                // Seleccionar la primera fuente disponible de Perú
                if (blobSelect.options.length > 1) {
                    blobSelect.selectedIndex = 1;
                    blobSelect.dispatchEvent(new Event('change'));

                    // Esperar y cargar datos
                    await new Promise(resolve => setTimeout(resolve, 200));
                    await handleDataLoad();
                } else {
                    showContextMessage({
                        type: 'warning',
                        title: 'Sin datos',
                        message: 'No hay fuentes de datos disponibles para Perú'
                    });
                }

            } catch (error) {
                console.error('Error en Quick Action Perú:', error);
                showContextMessage({
                    type: 'error',
                    title: 'Error',
                    message: 'No se pudo cargar los datos de Perú'
                });
            }
        }

        /**
         * Carga favorito desde Quick Actions
         */
        function selectFavoritesQuickAction() {
            const hasFavorite = FavoritesManager.hasFavorite();

            if (!hasFavorite) {
                quickActionsModal.hide();
                showContextMessage({
                    type: 'info',
                    title: 'Sin favorito',
                    message: 'Aún no tienes ningún favorito guardado. Carga una fuente de datos y guarda tu primera configuración.'
                });
                return;
            }

            quickActionsModal.hide();
            loadFavoriteHandler();
        }

        // Event listeners de Quick Actions
        quickActionChile.addEventListener('click', selectChileQuickAction);
        quickActionPeru.addEventListener('click', selectPeruQuickAction);
        quickActionFavorites.addEventListener('click', selectFavoritesQuickAction);

        // Soporte para teclado en las action cards
        [quickActionChile, quickActionPeru, quickActionFavorites].forEach(card => {
            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    card.click();
                }
            });
        });

        // ===== FUNCIONES Y LÓGICA DE ÚLTIMO ESTADO USADO =====

        const LAST_STATE_KEY = 'reportes_last_state';
        const LAST_STATE_MAX_AGE = 24 * 60 * 60 * 1000; // 24 horas en milisegundos

        /**
         * Guarda el último estado usado
         */
        function saveLastUsedState() {
            try {
                const { currentBlobDisplayName } = getState();
                if (!currentBlobDisplayName) return;

                const state = {
                    country: countrySelect.value,
                    source: currentBlobDisplayName,
                    sourceDisplayName: blobSelect.options[blobSelect.selectedIndex]?.text || '',
                    timestamp: Date.now()
                };

                localStorage.setItem(LAST_STATE_KEY, JSON.stringify(state));
            } catch (error) {
                console.error('Error guardando último estado:', error);
            }
        }

        /**
         * Restaura el último estado usado
         */
        async function restoreLastState() {
            try {
                const storedState = localStorage.getItem(LAST_STATE_KEY);
                if (!storedState) return;

                const lastState = JSON.parse(storedState);

                // Verificar edad del estado
                const age = Date.now() - lastState.timestamp;
                if (age > LAST_STATE_MAX_AGE) {
                    // Estado muy antiguo, limpiar
                    localStorage.removeItem(LAST_STATE_KEY);
                    return;
                }

                // Formatear tiempo transcurrido
                const hoursAgo = Math.floor(age / (60 * 60 * 1000));
                const minutesAgo = Math.floor((age % (60 * 60 * 1000)) / (60 * 1000));
                const timeAgo = hoursAgo > 0 ? `hace ${hoursAgo}h` : `hace ${minutesAgo}min`;

                // Mostrar notificación con opción de restaurar
                showContextMessage({
                    type: 'info',
                    title: '¿Continuar donde lo dejaste?',
                    message: `Última consulta: ${lastState.sourceDisplayName} (${timeAgo})`,
                    duration: 10000, // 10 segundos
                    action: {
                        label: 'Cargar',
                        callback: async () => {
                            try {
                                // Seleccionar país
                                if (countrySelect.value !== lastState.country) {
                                    countrySelect.value = lastState.country;
                                    countrySelect.dispatchEvent(new Event('change'));
                                    await new Promise(resolve => setTimeout(resolve, 300));
                                }

                                // Seleccionar fuente
                                const sourceOption = Array.from(blobSelect.options).find(
                                    opt => opt.textContent === lastState.sourceDisplayName
                                );

                                if (sourceOption) {
                                    blobSelect.value = sourceOption.value;
                                    blobSelect.dispatchEvent(new Event('change'));
                                    await new Promise(resolve => setTimeout(resolve, 200));

                                    // Cargar datos
                                    await handleDataLoad();
                                }
                            } catch (error) {
                                console.error('Error restaurando último estado:', error);
                                showContextMessage({
                                    type: 'error',
                                    title: 'Error',
                                    message: 'No se pudo restaurar el último estado'
                                });
                            }
                        }
                    }
                });

            } catch (error) {
                console.error('Error restaurando último estado:', error);
            }
        }

        /**
         * Verifica y muestra opción de restaurar último estado
         */
        function checkAndRestoreLastState() {
            const { currentBlobDisplayName } = getState();

            // Solo mostrar si no hay datos cargados actualmente
            if (!currentBlobDisplayName || Object.keys(dataSourceCache).length === 0) {
                // Esperar un poco para que Quick Actions tenga prioridad
                setTimeout(() => {
                    // Solo mostrar si el usuario no interactuó con Quick Actions
                    const { currentBlobDisplayName: currentState } = getState();
                    if (!currentState || Object.keys(dataSourceCache).length === 0) {
                        restoreLastState();
                    }
                }, 3000); // 3 segundos de espera
            }
        }

        // ===== EVENT LISTENERS DE FAVORITOS (SISTEMA SIMPLIFICADO) =====

        // Guardar favorito con un solo clic
        saveFavoritesOption.addEventListener('click', (e) => {
            e.preventDefault();
            saveFavoriteHandler();
        });

        // Cargar favorito con un solo clic
        loadFilterStateButton.addEventListener('click', (e) => {
            e.preventDefault();
            loadFavoriteHandler();
        });

        // ===== EVENT LISTENERS ANTIGUOS COMENTADOS (REEMPLAZADOS POR SISTEMA DE FAVORITOS MEJORADO) =====
        /*
         * Estos event listeners antiguos usaban el sistema de favoritos basado en config.ini del backend.
         * Han sido reemplazados por el nuevo sistema basado en localStorage con múltiples favoritos.
         * Se mantienen comentados por si se necesita referencia o rollback.
         *
        saveFilterStateButton.addEventListener('click', async () => {
            const { currentBlobDisplayName } = getState();
            if (!currentBlobDisplayName) {
                alert('Selecciona y carga una fuente de datos primero.');
                return;
            }

            setState({ isLoading: true, statusMessage: 'Guardando estado de filtros...' });

            try {
                const { value_filters } = getFilterPayload();
                const stateToSave = {
                    value_filters: value_filters,
                    selected_columns: currentSelectedDisplayColumns,
                    extend_sku_search: extendSkuHijoCheckbox ? extendSkuHijoCheckbox.checked : false
                };
                const response = await fetch(`${API_BASE}/api/state/save/${currentBlobDisplayName}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(stateToSave)
                });
                if (!response.ok) throw new Error(`Error del servidor: ${await response.text()}`);

                const result = await response.json();
                setState({ statusMessage: result.message || "Estado guardado." });

            } catch (error) {
                console.error("Error guardando estado:", error);
                setState({ statusMessage: `Error al guardar: ${error.message}` });
            } finally {
                setState({ isLoading: false });
            }
        });

        loadFilterStateButton.addEventListener('click', async () => {
            const { currentBlobDisplayName } = getState();
            if (!currentBlobDisplayName) {
                alert('Selecciona una fuente de datos primero.');
                return;
            }

            setState({ isLoading: true, statusMessage: `Cargando estado para ${currentBlobDisplayName}...` });

            try {
                const response = await fetch(`${API_BASE}/api/state/load/${currentBlobDisplayName}`);
                if (!response.ok) throw new Error(`Error del servidor: ${await response.text()}`);

                const savedState = await response.json();

                if (savedState.message && !Object.keys(savedState.value_filters || {}).length && !(savedState.selected_columns || []).length) {
                    setState({ statusMessage: savedState.message });
                    return;
                }

                if (!dataSourceCache[currentBlobDisplayName]) {
                    await handleDataLoad();
                }

                const valueFiltersToApply = savedState.value_filters || {};
                filterControlsContainer.querySelectorAll('select.filter-select').forEach(select => {
                    const colName = select.dataset.column;
                    Array.from(select.options).forEach(option => {
                        option.selected = (valueFiltersToApply[colName] || []).includes(option.value);
                    });
                });

                const savedSelectedCols = (savedState.selected_columns || []).map(c => String(c).toLowerCase());
                if (columnsListboxContainer && savedSelectedCols.length > 0) {
                    currentSelectedDisplayColumns = [];
                    columnsListboxContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                        const isChecked = savedSelectedCols.includes(cb.value);
                        cb.checked = isChecked;
                        if (isChecked) {
                            currentSelectedDisplayColumns.push(cb.value);
                        }
                    });
                }

                if (extendSkuHijoCheckbox) {
                    extendSkuHijoCheckbox.checked = savedState.extend_sku_search || false;
                }

                setState({ statusMessage: 'Favoritos cargados. Haz clic en "Aplicar Filtros" para aplicarlos.' });

            } catch (error) {
                console.error("Error cargando estado:", error);
                setState({ statusMessage: `Error al cargar: ${error.message}` });
            } finally {
                setState({ isLoading: false });
            }
        });
        */

        // Event listener para descargar reporte desde el modal de resultados parciales
        document.getElementById('download-not-found-from-modal').addEventListener('click', () => {
            const detalle = window.detalleNoEncontradosGlobal;

            if (!detalle) {
                alert("No hay valores no encontrados para reportar.");
                return;
            }

            // Verificar si hay al menos un valor no encontrado
            const totalNoEncontrados = (detalle.skusHijo?.length || 0) +
                                      (detalle.skusPadre?.length || 0) +
                                      (detalle.tickets?.length || 0) +
                                      (detalle.lineamientos?.length || 0);

            if (totalNoEncontrados === 0) {
                alert("No hay valores no encontrados para reportar.");
                return;
            }

            // Construir el reporte con todas las secciones
            let content = "========================================\n";
            content += "  REPORTE DE VALORES NO ENCONTRADOS\n";
            content += "========================================\n";
            content += `Fecha: ${new Date().toLocaleString()}\n\n`;

            // Sección SKU Hijo
            if (detalle.skusHijo && detalle.skusHijo.length > 0) {
                content += "----------------------------------------\n";
                content += "SKU HIJO NO ENCONTRADOS\n";
                content += "----------------------------------------\n";
                content += detalle.skusHijo.join('\n') + '\n\n';
            }

            // Sección SKU Padre
            if (detalle.skusPadre && detalle.skusPadre.length > 0) {
                content += "----------------------------------------\n";
                content += "SKU PADRE NO ENCONTRADOS\n";
                content += "----------------------------------------\n";
                content += detalle.skusPadre.join('\n') + '\n\n';
            }

            // Sección Requerimientos (tickets)
            if (detalle.tickets && detalle.tickets.length > 0) {
                content += "----------------------------------------\n";
                content += "REQUERIMIENTOS NO ENCONTRADOS\n";
                content += "----------------------------------------\n";
                content += detalle.tickets.join('\n') + '\n\n';
            }

            // Sección Lineamientos (tickets de asunto)
            if (detalle.lineamientos && detalle.lineamientos.length > 0) {
                content += "----------------------------------------\n";
                content += "TICKETS NO ENCONTRADOS\n";
                content += "----------------------------------------\n";
                content += detalle.lineamientos.join('\n') + '\n\n';
            }

            content += "========================================\n";
            content += `Total valores no encontrados: ${totalNoEncontrados}\n`;
            content += "========================================\n";

            // Crear y descargar el archivo
            const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `Reporte_Valores_No_Encontrados_${new Date().toISOString().slice(0, 10)}.txt`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);

            // Cerrar el modal después de descargar
            const modal = bootstrap.Modal.getInstance(document.getElementById('partialResultsModal'));
            if (modal) modal.hide();

            logToBrowserConsole(`Reporte de valores no encontrados descargado: ${totalNoEncontrados} valores`, 'info');
        });
        
        // Column selection - con actualización automática de tabla
        selectAllColsButton.addEventListener('click', () => {
            columnsListboxContainer.querySelectorAll('input').forEach(cb => cb.checked = true);
            currentSelectedDisplayColumns = Array.from(columnsListboxContainer.querySelectorAll('input:checked')).map(cb => cb.value);
            // ⚡ Actualizar tabla automáticamente sin consulta backend
            updateTableColumnsOnly();
            logToBrowserConsole('Todas las columnas seleccionadas - tabla actualizada', 'info');
        });
        deselectAllColsButton.addEventListener('click', () => {
            columnsListboxContainer.querySelectorAll('input').forEach(cb => cb.checked = false);
            currentSelectedDisplayColumns = [];
            // ⚡ Actualizar tabla automáticamente (mostrará mensaje de "selecciona al menos una columna")
            updateTableColumnsOnly();
            logToBrowserConsole('Todas las columnas deseleccionadas - tabla actualizada', 'info');
        });

        // File uploads
        uploadSkuHijoButton.addEventListener('click', () => handleFileUpload(skuHijoFileInput, `${API_BASE}/api/files/upload/sku-hijo`, skuHijoStatus, 'SKU Hijo'));
        clearSkuHijoButton.addEventListener('click', () => handleFileClear(`${API_BASE}/api/files/sku-hijo`, skuHijoStatus, 'SKU Hijo')); // CORREGIDO
        uploadSkuPadreButton.addEventListener('click', () => handleFileUpload(skuPadreFileInput, `${API_BASE}/api/files/upload/sku-padre`, skuPadreStatus, 'SKU Padre'));
        clearSkuPadreButton.addEventListener('click', () => handleFileClear(`${API_BASE}/api/files/sku-padre`, skuPadreStatus, 'SKU Padre')); // CORREGIDO
        uploadTicketFileButton.addEventListener('click', () => handleFileUpload(ticketFileInput, `${API_BASE}/api/files/upload/ticket-file`, ticketFileStatus, 'Ticket'));
        clearTicketFileButton.addEventListener('click', () => handleFileClear(`${API_BASE}/api/files/ticket-file`, ticketFileStatus, 'Ticket')); // CORREGIDO

        // Tabs
        document.querySelectorAll(".tab-button").forEach(button => {
            button.addEventListener('click', (event) => {
                const tabName = event.currentTarget.dataset.tab;
                document.querySelectorAll(".tab-content").forEach(tab => tab.style.display = "none");
                document.querySelectorAll(".tab-button").forEach(link => link.classList.remove("active"));
                document.getElementById(tabName).style.display = "block";
                event.currentTarget.classList.add("active");
            });
        });

    }

    // FUNCIÓN OBSOLETA: Ya no se necesita controlar visibilidad de opciones de dropdown
    // El nuevo sistema usa un solo botón con caché inteligente automático
    function updateCacheOptionsVisibility(blobDisplayName) {
        // Función deshabilitada - ya no hay dropdown de opciones
        return;
    }

    // Función para actualizar la disponibilidad de los botones
    function updateButtonAvailability() {
        const state = getState();
        const currentBlobDisplayName = state.currentBlobDisplayName;
        const selectedBlobName = blobSelect ? blobSelect.value : currentBlobDisplayName;
        const hasData = currentBlobDisplayName !== null && currentBlobDisplayName !== '';

        // Actualizar visibilidad de opciones de cache según la base actual
        if (currentBlobDisplayName) {
            updateCacheOptionsVisibility(currentBlobDisplayName);
        }

        // Verificar caché local (frontend), caché del servidor, y caché persistente
        const hasLocalCache = hasData && dataSourceCache[currentBlobDisplayName];
        const hasServerCache = serverCacheStatus && serverCacheStatus.has_data_loaded && 
                              (selectedBlobName === serverCacheStatus.current_blob_display_name || 
                               currentBlobDisplayName === serverCacheStatus.current_blob_display_name);
        const hasPersistentCache = currentBlobDisplayName && persistentCacheStatus[currentBlobDisplayName] && 
                                  persistentCacheStatus[currentBlobDisplayName].has_cache;
        const hasCachedData = hasLocalCache || hasServerCache || hasPersistentCache;
        
        const hasFilteredData = hasData && (state.rowCount?.filtered > 0 || state.dataForDisplay?.length > 0);
        const isProcessing = state.loadingDetails?.isProcessing || false;
        
        logToBrowserConsole(`updateButtonAvailability - hasData: ${hasData}, currentBlobDisplayName: '${currentBlobDisplayName}', selectedBlobName: '${selectedBlobName}', hasLocalCache: ${hasLocalCache}, hasServerCache: ${hasServerCache}, hasPersistentCache: ${hasPersistentCache}, hasCachedData: ${hasCachedData}, isProcessing: ${isProcessing}`, 'debug');
        
        // "Carga Completa" siempre disponible si hay una fuente seleccionada y no se está procesando
        if (loadDataButton) {
            const isDisabled = !hasData || isProcessing;
            loadDataButton.disabled = isDisabled;

            // Actualizar tooltip según estado
            let reason = '';
            if (!hasData) reason = 'Selecciona una fuente de datos primero';
            else if (isProcessing) reason = 'Espera a que termine la operación actual';

            updateButtonTooltip(
                loadDataButton,
                isDisabled,
                'Cargar datos desde la fuente seleccionada',
                reason
            );
        }

        // Ya no hay botones de dropdown (sistema de caché inteligente automático)

        // Otros botones que requieren datos cargados
        const needsDataButtons = [
            { btn: applyFiltersButton, text: 'Aplicar los filtros configurados a los datos cargados' },
            { btn: saveFavoritesOption, text: 'Guardar la configuración actual de filtros para uso futuro' },
            { btn: clearAllFiltersButton, text: 'Limpiar todos los filtros activos y restaurar vista completa' },
            { btn: loadFilterStateButton, text: 'Cargar un favorito guardado previamente' }
        ];
        needsDataButtons.forEach(({ btn, text }) => {
            if (btn && !isProcessing) {
                const isDisabled = !hasData;
                btn.disabled = isDisabled;

                // Actualizar tooltip
                updateButtonTooltip(
                    btn,
                    isDisabled,
                    text,
                    'Debes cargar datos primero'
                );
            }
        });
        
        // Botones de exportación solo disponibles si hay datos filtrados y no se está exportando
        if (exportExcelButton) {
            const isDisabled = !hasFilteredData || isExporting || isProcessing;
            exportExcelButton.disabled = isDisabled;

            let reason = '';
            if (!hasFilteredData) reason = 'Debes cargar y filtrar datos primero';
            else if (isExporting) reason = 'Ya hay una exportación en proceso';
            else if (isProcessing) reason = 'Espera a que termine la operación actual';

            updateButtonTooltip(
                exportExcelButton,
                isDisabled,
                'Exportar los datos filtrados a un archivo Excel con formato',
                reason
            );
        }

        if (exportCsvButton) {
            const isDisabled = !hasFilteredData || isExporting || isProcessing;
            exportCsvButton.disabled = isDisabled;

            let reason = '';
            if (!hasFilteredData) reason = 'Debes cargar y filtrar datos primero';
            else if (isExporting) reason = 'Ya hay una exportación en proceso';
            else if (isProcessing) reason = 'Espera a que termine la operación actual';

            updateButtonTooltip(
                exportCsvButton,
                isDisabled,
                'Exportar los datos filtrados a un archivo CSV simple',
                reason
            );
        }

        // Opciones de tabla disponibles cuando hay datos filtrados
        if (tableOptionsDropdown) {
            const isDisabled = !hasFilteredData || isProcessing;
            tableOptionsDropdown.disabled = isDisabled;

            let reason = '';
            if (!hasFilteredData) reason = 'Debes cargar datos primero';
            else if (isProcessing) reason = 'Espera a que termine la operación actual';

            updateButtonTooltip(
                tableOptionsDropdown,
                isDisabled,
                'Opciones de visualización de la tabla',
                reason
            );
        }
    }

    // NUEVA FUNCIÓN: Actualizar indicadores de cache
    function updateCacheIndicators() {
        if (!blobSelect) return;
        
        Array.from(blobSelect.options).forEach(option => {
            if (option.value && option.value !== "") {
                const isInCache = dataSourceCache[option.value] !== undefined;
                const baseName = option.value;
                const cacheIndicator = isInCache ? ' 📋' : '';
                
                // Solo actualizar si ha cambiado
                const expectedText = baseName + cacheIndicator;
                if (option.textContent !== expectedText) {
                    option.textContent = expectedText;
                }
            }
        });
        
        // Actualizar también información adicional de cache en la barra de estado
        const cacheCount = Object.keys(dataSourceCache).length;
        if (cacheCount > 0) {
            const cacheInfo = ` (${cacheCount} base${cacheCount > 1 ? 's' : ''} en cache)`;
            if (statusMessage && !statusMessage.textContent.includes('en cache')) {
                const currentStatus = statusMessage.textContent;
                if (!currentStatus.includes('cache')) {
                    statusMessage.textContent = currentStatus + cacheInfo;
                }
            }
        }
    }

    // Llamar a la función inicialmente
    updateButtonAvailability();

    // Función para consultar el estado del caché del servidor
    async function checkServerCacheStatus() {
        try {
            const response = await fetch(`${API_BASE}/api/cache/status`);
            if (!response.ok) throw new Error(`HTTP error ${response.status}`);
            const cacheStatus = await response.json();
            
            // Si hay datos cargados en el servidor, actualizar la interfaz
            if (cacheStatus.has_data_loaded && cacheStatus.current_blob_display_name) {
                // Actualizar el estado local con los datos del servidor
                setState({
                    currentBlobDisplayName: cacheStatus.current_blob_display_name,
                    statusMessage: `Base '${cacheStatus.current_blob_display_name}' disponible en caché (${cacheStatus.row_count.toLocaleString()} filas)`
                });
                
                // Loaded bases panel removed - cache info shown in selector only
                
                // Habilitar botones relevantes
                updateButtonAvailability();
                
                logToBrowserConsole(`Base '${cacheStatus.current_blob_display_name}' encontrada en caché del servidor (${cacheStatus.row_count} filas)`, 'info');
            }
            
            // Almacenar el estado del caché del servidor globalmente
            serverCacheStatus = cacheStatus;
            return cacheStatus;
        } catch (error) {
            console.error('Error consultando estado del caché:', error);
            serverCacheStatus = null;
            return null;
        }
    }

    // Function removed - loaded bases panel eliminated with persistent cache system

    // Función para realizar carga rápida desde el caché del servidor
    window.loadFromServerCache = async function(blobDisplayName) {
        try {
            // Activar el overlay de carga
            setState({ 
                statusMessage: `Cargando '${blobDisplayName}' desde caché...`,
                loadingDetails: {
                    message: 'Carga Rápida desde Caché',
                    submessage: `Recuperando datos de '${blobDisplayName}' desde el servidor...`,
                    isProcessing: true
                }
            });
            logToBrowserConsole(`Iniciando carga rápida de '${blobDisplayName}' desde caché del servidor`, 'info');
            
            // Realizar una petición de filtro vacía para obtener los datos desde el servidor
            // Esto activará la lógica de sincronización automática que ya existe
            const filterRequest = {
                blob_filename: blobDisplayName,
                value_filters: {},
                selected_display_columns: null,
                page: 1,
                page_size: 100,
                use_sku_hijo_file: false,
                extend_sku_hijo: false,
                sku_hijo_manual_list: null,
                use_sku_padre_file: false,
                sku_padre_manual_list: null,
                use_ticket_file: false,
                ticket_manual_list: null,
                lineamiento_manual_list: null
            };
            
            const response = await fetch(`${API_BASE}/api/data/filter`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(filterRequest)
            });
            
            if (!response.ok) throw new Error(`HTTP error ${response.status}`);
            const result = await response.json();
            
            // Actualizar el estado de la aplicación con los datos cargados
            setState({
                currentBlobDisplayName: blobDisplayName,
                currentBlobFilename: result.current_blob_filename || blobDisplayName,
                dataForDisplay: result.data || [],
                rowCount: {
                    original: result.row_count_original || 0,
                    filtered: result.row_count_filtered || 0,
                    display: result.data ? result.data.length : 0
                },
                statusMessage: `Base '${blobDisplayName}' cargada desde caché (${(result.row_count_original || 0).toLocaleString()} filas)`,
                loadingDetails: {
                    message: '',
                    submessage: '',
                    isProcessing: false
                }
            });
            
            // CRÍTICO: Crear entrada en caché local para que funcione "aplicar filtros"
            dataSourceCache[blobDisplayName] = {
                fileInfo: {
                    displayName: blobDisplayName,
                    fileName: result.current_blob_filename || blobDisplayName,
                    originalRowCount: result.row_count_original || 0
                },
                columnsData: result.columns_in_data || [],
                lastUpdate: new Date().toISOString()
            };
            
            // Cargar configuración de filtros para esta base
            try {
                const settingsResponse = await fetch(`${API_BASE}/api/config/settings/${blobDisplayName}`);
                if (settingsResponse.ok) {
                    const blobSettings = await settingsResponse.json();
                    setState({ 
                        hiddenColumnsConfig: Array.isArray(blobSettings.hide_columns) ? 
                            blobSettings.hide_columns.map(c => String(c).toLowerCase()) : 
                            []
                    });
                    
                    // CRÍTICO: Obtener opciones de filtro correctamente
                    // Como el endpoint ${API_BASE}/api/data/filter incluye sincronización automática, 
                    // las filter_options deberían estar disponibles después de esa llamada
                    
                    // Intentar obtener filter_options del caché del backend mediante una segunda llamada
                    let filterOptionsObtained = {};
                    try {
                        const filterOnlyRequest = {
                            blob_filename: blobDisplayName,
                            value_filters: {},
                            selected_display_columns: [],
                            page: 1,
                            page_size: 1 // Solo necesitamos obtener las filter_options, no los datos
                        };
                        
                        const filterOnlyResponse = await fetch(`${API_BASE}/api/data/filter`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(filterOnlyRequest)
                        });
                        
                        if (filterOnlyResponse.ok) {
                            const filterOnlyData = await filterOnlyResponse.json();
                            
                            // Ahora que el backend está sincronizado, hacer una llamada simple para obtener filter_options
                            const loadResponse = await fetch(`${API_BASE}/api/data/load/${blobDisplayName}`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' }
                            });
                            
                            if (loadResponse.ok) {
                                const loadData = await loadResponse.json();
                                filterOptionsObtained = loadData.filter_options || {};
                            }
                        }
                    } catch (filterError) {
                        console.warn('Error obteniendo opciones de filtro:', filterError);
                    }
                    
                    // Agregar configuración al caché
                    dataSourceCache[blobDisplayName].filterOptions = filterOptionsObtained;
                    dataSourceCache[blobDisplayName].filterConfig = blobSettings.filter_columns || [];
                    dataSourceCache[blobDisplayName].fileInfo.columns = result.columns_in_data || [];
                    
                    
                    // CRUCIAL: Habilitar pestañas "Filtros" y "Columnas" - ESTA ERA LA LÍNEA FALTANTE
                    populateFilterControls(filterOptionsObtained, blobSettings.filter_columns || []);
                    populateColumnsListbox(result.columns_in_data || [], getState().hiddenColumnsConfig);

                    // NUEVO: Actualizar visibilidad de filtros según configuración de la base
                    await updateFilterVisibility(blobDisplayName);
                }
            } catch (settingsError) {
                console.warn('Error cargando configuración de filtros:', settingsError);
            }
            
            // Actualizar la tabla y controles
            renderDataTable(result.data || [], result.columns_in_data || []);
            updateButtonAvailability();
            
            // Seleccionar la base en los dropdowns si corresponde
            const option = Array.from(blobSelect.options).find(opt => opt.value === blobDisplayName);
            if (option) {
                blobSelect.value = blobDisplayName;
                // Actualizar país correspondiente
                for (const [country, sources] of Object.entries(sourcesByCountry)) {
                    if (sources.some(source => source.display_name === blobDisplayName)) {
                        countrySelect.value = country;
                        populateBlobSelect(country);
                        blobSelect.value = blobDisplayName;
                        break;
                    }
                }
            }
            
            logToBrowserConsole(`Carga rápida completada para '${blobDisplayName}' (${(result.row_count_original || 0).toLocaleString()} filas)`, 'info');
            
            // Loaded bases panel removed - cache status shown in selector
            
        } catch (error) {
            console.error('Error en carga rápida:', error);
            setState({ 
                statusMessage: `Error en carga rápida: ${error.message}`,
                loadingDetails: {
                    message: '',
                    submessage: '',
                    isProcessing: false
                }
            });
            logToBrowserConsole(`Error en carga rápida de '${blobDisplayName}': ${error.message}`, 'error');
        }
    };

    // --- INICIALIZACIÓN ---
    async function init() {
        subscribeToStoreChanges();
        setupEventListeners();
        initNetworkMonitor(); // Inicializar monitor de conectividad
        updateHeaderStyle(null, true);
        await fetchBlobOptions();
        
        // Consultar estado del caché del servidor después de cargar la configuración
        await checkServerCacheStatus();
        
        // Actualizar disponibilidad de botones después de consultar el caché del servidor
        updateButtonAvailability();
        
        if (loadFilterStateButton) loadFilterStateButton.disabled = true;
        connectToLogStream();
        // Click first tab
        const firstTab = document.querySelector('.tab-button');
        if (firstTab) firstTab.click();
        
        // Actualizar indicadores de cache cada 30 segundos
        setInterval(updateCacheIndicators, 30000);
    }

    // init(); // Ahora se llama desde waitForServer() después de verificar que el servidor esté listo

    // --- LÓGICA DE MANEJO DE DATOS ---

    function clearDataTable() {
        // Limpiar la tabla de datos
        if (dataTableHead) {
            dataTableHead.innerHTML = '';
        }
        if (dataTableBody) {
            // Usar el nuevo estado por defecto
            const currentBase = getState().currentBlobDisplayName;
            setTableState('no-query', currentBase);
        }
        if (paginationContainer) {
            paginationContainer.innerHTML = '';
        }
        if (rowCountMessage) {
            rowCountMessage.textContent = '0';
        }
        
        logToBrowserConsole('Tabla de datos limpiada', 'debug');
    }

    function setTableState(state, baseName = null) {
        // Función para establecer diferentes estados de la tabla de datos
        if (!dataTableBody) return;
        
        let message = '';
        let icon = '';
        let className = 'text-center text-muted p-3';
        
        switch (state) {
            case 'loading':
                message = 'Cargando datos...';
                icon = '<i class="bi bi-arrow-clockwise me-2"></i>';
                className = 'text-center text-primary p-3';
                break;
            case 'no-data':
                message = 'No hay datos disponibles para mostrar';
                icon = '<i class="bi bi-exclamation-circle me-2"></i>';
                className = 'text-center text-warning p-3';
                break;
            case 'no-query':
                // Verificar si la base está realmente cargada en el cache
                const isBaseLoaded = baseName && dataSourceCache[baseName];
                if (isBaseLoaded) {
                    message = `Base "${baseName}" cargada. Realiza una consulta para ver los datos.`;
                    icon = '<i class="bi bi-search me-2"></i>';
                    className = 'text-center text-info p-3';
                } else if (baseName) {
                    message = `Base "${baseName}" seleccionada. Carga la base para realizar consultas.`;
                    icon = '<i class="bi bi-download me-2"></i>';
                    className = 'text-center text-warning p-3';
                } else {
                    message = 'Selecciona una base de datos y cárgala para realizar consultas.';
                    icon = '<i class="bi bi-database me-2"></i>';
                    className = 'text-center text-muted p-3';
                }
                break;
            case 'error':
                message = 'Error al cargar los datos. Intenta nuevamente.';
                icon = '<i class="bi bi-x-circle me-2"></i>';
                className = 'text-center text-danger p-3';
                break;
            case 'empty':
                message = 'No se encontraron resultados para los filtros aplicados';
                icon = '<i class="bi bi-inbox me-2"></i>';
                className = 'text-center text-muted p-3';
                break;
            default:
                message = 'Estado desconocido';
                icon = '<i class="bi bi-question-circle me-2"></i>';
                className = 'text-center text-muted p-3';
        }
        
        dataTableBody.innerHTML = `<tr><td colspan=\"100\" class=\"${className}\">${icon}${message}</td></tr>`;
        logToBrowserConsole(`Estado de tabla establecido: ${state}`, 'debug');
    }

    // --- LÓGICA DE MANEJO DE DATOS ---

    function populateFilterControls(filterOptions, filterColsCfg) {
        if (!filterControlsContainer) return;
        filterControlsContainer.innerHTML = '';
        if (!filterOptions || Object.keys(filterOptions).length === 0) {
            filterControlsContainer.innerHTML = '<p class="text-muted small">No hay filtros disponibles para esta fuente de datos.</p>';
            return;
        }

        const sortedFilterKeys = Object.keys(filterOptions).sort();

        sortedFilterKeys.forEach(key => {
            const options = filterOptions[key] || [];
            const filterId = `filter-${key.replace(/\s/g, '-')}`;

            const filterGroup = document.createElement('div');
            filterGroup.className = 'mb-3';

            const titleElement = document.createElement('div');
            titleElement.className = 'btn btn-sm btn-outline-secondary w-100 text-start mb-2';
            titleElement.style.cursor = 'default';
            titleElement.innerHTML = `<i class="bi bi-chevron-right me-2"></i><strong>${key}</strong>`;
            filterGroup.appendChild(titleElement);

            const select = document.createElement('select');
            select.multiple = true;
            select.className = 'form-select form-select-sm filter-select';
            select.id = filterId;
            select.dataset.column = key;
            select.size = Math.min(Math.max(options.length, 3), 6); 

            options.forEach(option => {
                const opt = document.createElement('option');
                opt.value = option;
                opt.textContent = option === '' ? '[Vacío]' : option;
                select.appendChild(opt);
            });

            if (options.length === 0) {
                const opt = document.createElement('option');
                opt.textContent = 'No hay opciones';
                opt.disabled = true;
                select.appendChild(opt);
            }
            
            filterGroup.appendChild(select);
            filterControlsContainer.appendChild(filterGroup);
        });
    }

    // ⚡ NUEVA FUNCIÓN: Re-renderizar tabla solo cambiando columnas visibles (sin consulta backend)
    function updateTableColumnsOnly() {
        const { dataForDisplay, currentBlobDisplayName } = getState();

        // Verificar que hay datos cargados
        if (!dataForDisplay || dataForDisplay.length === 0) {
            logToBrowserConsole('No hay datos para actualizar columnas', 'debug');
            return;
        }

        // Verificar que hay columnas seleccionadas
        if (!currentSelectedDisplayColumns || currentSelectedDisplayColumns.length === 0) {
            logToBrowserConsole('No hay columnas seleccionadas para mostrar', 'warning');
            dataTableBody.innerHTML = '<tr><td colspan="100" class="text-center text-muted p-3">Selecciona al menos una columna para visualizar</td></tr>';
            dataTableHead.innerHTML = '';
            return;
        }

        // Re-renderizar la tabla con las columnas seleccionadas
        logToBrowserConsole(`Actualizando vista de tabla con ${currentSelectedDisplayColumns.length} columnas seleccionadas (sin consulta backend)`, 'info');
        renderDataTable(dataForDisplay, currentSelectedDisplayColumns);

        // Actualizar la caché con las nuevas columnas seleccionadas
        if (currentBlobDisplayName && dataSourceCache[currentBlobDisplayName]) {
            dataSourceCache[currentBlobDisplayName].selectedColumns = [...currentSelectedDisplayColumns];
            logToBrowserConsole('Columnas seleccionadas guardadas en caché', 'debug');
        }
    }

    function populateColumnsListbox(allCols, hiddenCols) {
        if (!columnsListboxContainer) return;
        columnsListboxContainer.innerHTML = '';
        currentSelectedDisplayColumns = [];
        const visibleCols = allCols.filter(col => !hiddenCols.includes(col));
        if (visibleCols.length === 0) {
            columnsListboxContainer.innerHTML = '<small class="text-muted d-block p-2">No hay columnas.</small>';
            return;
        }
        visibleCols.forEach(colName => {
            const div = document.createElement('div');
            div.className = 'form-check form-check-sm';
            const id = `col-cb-${colName.replace(/[^a-zA-Z0-9]/g, '')}`;
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'form-check-input';
            checkbox.id = id;
            checkbox.value = colName;
            checkbox.checked = true;

            // ⚡ MEJORA: Actualización automática e instantánea de columnas
            checkbox.addEventListener('change', () => {
                // Actualizar array de columnas seleccionadas
                currentSelectedDisplayColumns = Array.from(columnsListboxContainer.querySelectorAll('input:checked')).map(cb => cb.value);

                // Re-renderizar tabla automáticamente sin consulta backend
                updateTableColumnsOnly();

                logToBrowserConsole(`Columna "${colName}" ${checkbox.checked ? 'seleccionada' : 'deseleccionada'} - tabla actualizada`, 'debug');
            });

            const label = document.createElement('label');
            label.className = 'form-check-label';
            label.htmlFor = id;
            label.textContent = colName;
            div.append(checkbox, label);
            columnsListboxContainer.append(div);
            currentSelectedDisplayColumns.push(colName);
        });
    }

    /**
     * Actualiza la visibilidad de los filtros según configuración de la base de datos.
     * @param {string} blobDisplayName - Nombre de la base de datos
     */
    async function updateFilterVisibility(blobDisplayName) {
        try {
            const response = await fetch(
                `${API_BASE}/api/config/filter-visibility/${encodeURIComponent(blobDisplayName)}`
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const config = await response.json();

            // Actualizar visibilidad de filtros estándar
            const filterElements = {
                'ticket-filter-section': config.show_ticket_filter,
                'lineamiento-filter-section': config.show_lineamiento_filter
            };

            // Controlar visibilidad de secciones de filtros especiales
            for (const [elementId, shouldShow] of Object.entries(filterElements)) {
                const element = document.getElementById(elementId);
                if (element) {
                    element.style.display = shouldShow ? 'block' : 'none';
                    logToBrowserConsole(`${elementId} ${shouldShow ? 'mostrado' : 'ocultado'}`, 'debug');
                } else {
                    logToBrowserConsole(`⚠️ Elemento ${elementId} no encontrado en el DOM`, 'warn');
                }
            }

            // Controlar visibilidad de filtros SKU (buscar contenedor padre)
            const skuHijoSection = document.getElementById('collapseSkuHijo');
            if (skuHijoSection) {
                const skuHijoParent = skuHijoSection.parentElement;
                if (skuHijoParent && skuHijoParent.classList.contains('sku-filter-section')) {
                    skuHijoParent.style.display = config.show_sku_hijo_filter ? 'block' : 'none';
                    logToBrowserConsole(`SKU Hijo filter ${config.show_sku_hijo_filter ? 'mostrado' : 'ocultado'}`, 'debug');
                }
            }

            const skuPadreSection = document.getElementById('collapseSkuPadre');
            if (skuPadreSection) {
                const skuPadreParent = skuPadreSection.parentElement;
                if (skuPadreParent && skuPadreParent.classList.contains('sku-filter-section')) {
                    skuPadreParent.style.display = config.show_sku_padre_filter ? 'block' : 'none';
                    logToBrowserConsole(`SKU Padre filter ${config.show_sku_padre_filter ? 'mostrado' : 'ocultado'}`, 'debug');
                }
            }

            // Renderizar filtros personalizados de texto
            renderCustomTextFilters(config.custom_text_filters || [], blobDisplayName);

            logToBrowserConsole(
                `Filtros configurados para ${blobDisplayName}: Ticket=${config.show_ticket_filter}, ` +
                `Lineamiento=${config.show_lineamiento_filter}, ` +
                `SKU Hijo=${config.show_sku_hijo_filter}, ` +
                `SKU Padre=${config.show_sku_padre_filter}, ` +
                `Custom=${(config.custom_text_filters || []).length}`,
                'info'
            );
        } catch (error) {
            logToBrowserConsole(`Error actualizando visibilidad de filtros: ${error}`, 'error');
            console.error('Error en updateFilterVisibility:', error);
            // Fallback: mostrar todos los filtros si hay error
            showAllFilters();
        }
    }

    /**
     * Renderiza filtros personalizados de texto para búsqueda por coincidencias.
     * @param {Array<string>} customFilters - Lista de nombres de columnas para filtros personalizados
     * @param {string} blobDisplayName - Nombre de la base de datos
     */
    function renderCustomTextFilters(customFilters, blobDisplayName) {
        // Buscar contenedor de filtros personalizados (crear si no existe)
        let customContainer = document.getElementById('custom-filters-container');

        if (!customContainer) {
            customContainer = document.createElement('div');
            customContainer.id = 'custom-filters-container';
            customContainer.className = 'custom-filters-section';

            // Insertar después de lineamiento-filter-section
            const lineamientoSection = document.getElementById('lineamiento-filter-section');
            if (lineamientoSection) {
                lineamientoSection.insertAdjacentElement('afterend', customContainer);
            } else {
                // Fallback: insertar al final del contenedor de códigos
                const codigosTabContent = document.querySelector('#codigos .tab-pane-content');
                if (codigosTabContent) {
                    codigosTabContent.appendChild(customContainer);
                }
            }
        }

        // Limpiar filtros anteriores
        customContainer.innerHTML = '';

        // Si no hay filtros personalizados, salir
        if (!customFilters || customFilters.length === 0) {
            return;
        }

        // Renderizar cada filtro personalizado
        customFilters.forEach(columnName => {
            const filterHtml = createCustomTextFilterHTML(columnName);
            customContainer.insertAdjacentHTML('beforeend', filterHtml);
        });

        logToBrowserConsole(
            `Renderizados ${customFilters.length} filtros personalizados de texto: ${customFilters.join(', ')}`,
            'info'
        );
    }

    /**
     * Crea el HTML para un filtro personalizado de texto.
     * @param {string} columnName - Nombre de la columna
     * @returns {string} HTML del filtro
     */
    function createCustomTextFilterHTML(columnName) {
        const filterId = `custom-filter-${columnName.replace(/\s/g, '-').replace(/[^a-zA-Z0-9-]/g, '')}`;
        const label = columnName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

        return `
            <div class="mb-3" id="${filterId}-section">
                <button class="btn btn-sm btn-outline-secondary w-100 text-start filter-collapse-toggle"
                        type="button" data-bs-toggle="collapse"
                        data-bs-target="#collapse-${filterId}"
                        aria-expanded="false"
                        aria-controls="collapse-${filterId}">
                    <i class="bi bi-chevron-right me-2 filter-collapse-icon"></i>
                    <strong>Filtro: ${label}</strong>
                </button>
                <div class="collapse" id="collapse-${filterId}">
                    <div class="card card-body p-2 mt-1 filter-select-card">
                        <textarea
                            id="${filterId}-input"
                            class="form-control form-control-sm custom-text-filter-input"
                            rows="3"
                            placeholder="Ingrese valores a buscar (uno por línea)"
                            data-column="${columnName}"></textarea>
                        <small class="text-muted mt-1">
                            Busca coincidencias parciales en la columna "${columnName}". Un valor por línea.
                        </small>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Muestra todos los filtros (fallback de seguridad).
     */
    function showAllFilters() {
        const allFilterSections = [
            'ticket-filter-section',
            'lineamiento-filter-section'
        ];

        allFilterSections.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.display = 'block';
            }
        });

        // Mostrar secciones SKU
        const skuSections = document.querySelectorAll('.sku-filter-section');
        skuSections.forEach(section => {
            section.style.display = 'block';
        });

        logToBrowserConsole('Mostrando todos los filtros (modo seguro)', 'debug');
    }

    async function resetUIDataAndFilters() {
        logToBrowserConsole("Reseteando todos los filtros de la UI y los datos de la tabla.");

        // 1. Limpiar filtros de texto y áreas de texto (reutilizando la nueva función)
        clearManualFilterInputs();

        // 2. Resetear los selectores de filtros de columnas
        const selects = filterControlsContainer.querySelectorAll('select');
        selects.forEach(select => {
            if (select.tomselect) {
                select.tomselect.clear();
            } else {
                Array.from(select.options).forEach(option => option.selected = false);
            }
        });

        // 3. Resetear la selección de columnas a mostrar
        if (columnsListboxContainer) {
            const checkboxes = columnsListboxContainer.querySelectorAll('input[type="checkbox"]');
            const { hiddenColumnsConfig } = getState(); // Corregido para obtener del store
            const hiddenCols = hiddenColumnsConfig || [];
            checkboxes.forEach(cb => {
                cb.checked = !hiddenCols.includes(cb.value);
            });
        }
        
        // 4. Limpiar la tabla de datos y paginación
        clearDataTable();
        
        // 5. Resetear contador de filas (se actualiza automáticamente mediante el store)

        // 6. Resetear estado del store relevante
        setState({
            skuHijoFileLoaded: false,
            skuPadreFileLoaded: false,
            // No resetear 'dataForDisplay' o 'currentBlob...' aquí,
            // porque esta función se usa para LIMPIAR, no para descargar un nuevo archivo.
        });

        logToBrowserConsole("Reseteo de UI y filtros completado.");
    }

    // Event listener removed - loaded bases panel eliminated with persistent cache system

    // Loaded bases panel functions removed - using persistent cache system instead

    // Abrir la ventana modal al hacer clic en el botón flotante
    if (suggestionFab) {
        suggestionFab.addEventListener('click', () => {
            suggestionStatus.innerHTML = ''; // Limpiar estado anterior
            suggestionTextArea.value = ''; // Limpiar texto anterior
            sendSuggestionButton.disabled = false;
            suggestionModal.show();
        });
    }

    // Enviar la sugerencia al hacer clic en el botón "Enviar"
    sendSuggestionButton.addEventListener('click', async () => {
        const message = suggestionTextArea.value.trim();
        if (!message) {
            suggestionStatus.innerHTML = `<div class="alert alert-warning p-2 small">Por favor, escribe un mensaje.</div>`;
            return;
        }

        sendSuggestionButton.disabled = true;
        suggestionStatus.innerHTML = `<div class="alert alert-info p-2 small">Enviando...</div>`;

        try {
            const response = await fetch(FORMSPREE_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    _subject: "Sugerencia - App de Reportes", // ¡Aquí va el asunto!
                })
            });

            if (response.ok) {
                suggestionStatus.innerHTML = `<div class="alert alert-success p-2 small">¡Gracias! Tu mensaje ha sido enviado.</div>`;
                setTimeout(() => {
                    suggestionModal.hide();
                }, 2000); // Cierra la ventana después de 2 segundos
            } else {
                throw new Error('El servidor respondió con un error.');
            }
        } catch (error) {
            console.error("Error enviando sugerencia:", error);
            suggestionStatus.innerHTML = `<div class="alert alert-danger p-2 small">Error al enviar. Inténtalo de nuevo más tarde.</div>`;
            sendSuggestionButton.disabled = false;
        }
    });

    // Event listeners para modal de verificación de cache
    fullLoadRecommendationBtn.addEventListener('click', () => {
        // Activar carga completa cuando se recomiende
        handleDataLoad();
    });

    // NUEVO: Sincronizar verificaciones cuando se cierre el modal
    cacheVerificationModalElement.addEventListener('hidden.bs.modal', () => {
        const { currentBlobDisplayName } = getState();
        if (currentBlobDisplayName) {
            // Re-verificar estado de notificación para asegurar sincronización completa
            setTimeout(() => {
                checkForUpdates(currentBlobDisplayName);
                logToBrowserConsole(`Estado de notificación re-verificado al cerrar modal para '${currentBlobDisplayName}'`, 'debug');
            }, 100);
        }
    });

    // ⚡ OPTIMIZACIÓN: Event Listeners SIN auto-aplicación - Solo visuales
    if (skuHijoInput) {
        skuHijoInput.addEventListener('input', () => {
            showFilterInputPending(skuHijoInput, 'sku-hijo');
        });
        skuHijoInput.addEventListener('paste', () => {
            setTimeout(() => showFilterInputPending(skuHijoInput, 'sku-hijo'), 10);
        });
        // Aplicar al presionar Enter
        skuHijoInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleApplyFilters(1, false);
            }
        });
    }

    if (skuPadreInput) {
        skuPadreInput.addEventListener('input', () => {
            showFilterInputPending(skuPadreInput, 'sku-padre');
        });
        skuPadreInput.addEventListener('paste', () => {
            setTimeout(() => showFilterInputPending(skuPadreInput, 'sku-padre'), 10);
        });
        skuPadreInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleApplyFilters(1, false);
            }
        });
    }

    if (ticketFilterInput) {
        ticketFilterInput.addEventListener('input', () => {
            showFilterInputPending(ticketFilterInput, 'ticket');
        });
        ticketFilterInput.addEventListener('paste', () => {
            setTimeout(() => showFilterInputPending(ticketFilterInput, 'ticket'), 10);
        });
        ticketFilterInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleApplyFilters(1, false);
            }
        });
    }

    if (lineamientoFilterInput) {
        lineamientoFilterInput.addEventListener('input', () => {
            showFilterInputPending(lineamientoFilterInput, 'lineamiento');
        });
        lineamientoFilterInput.addEventListener('paste', () => {
            setTimeout(() => showFilterInputPending(lineamientoFilterInput, 'lineamiento'), 10);
        });
        lineamientoFilterInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleApplyFilters(1, false);
            }
        });
    }

    logToBrowserConsole('Event listeners configurados: filtros manuales (solo al hacer clic en Aplicar o Enter)', 'debug');
    
    // Event listener para el toggle de coloreado por prioridad
    if (priorityColoringToggle) {
        priorityColoringToggle.addEventListener('change', () => {
            logToBrowserConsole(`🎨 Toggle de prioridad cambiado a: ${priorityColoringToggle.checked}`, 'info');
            // Re-aplicar coloreado a las filas actuales de la tabla
            reapplyPriorityColoring();
        });
    }

    // ===== EVENT LISTENERS PARA MENÚ DE AYUDA =====
    // Opción "Ver Tutorial" - Inicia el tour interactivo
    if (showHelpOption) {
        showHelpOption.addEventListener('click', (e) => {
            e.preventDefault();
            startTour();
            logToBrowserConsole('Tour iniciado desde menú de ayuda', 'info');
        });
    }

    // ===== DARK MODE TOGGLE =====
    // Función para actualizar la UI del toggle según el tema actual
    function updateThemeToggleUI(theme) {
        if (theme === 'dark') {
            themeIcon.className = 'bi bi-sun me-2';
            themeText.textContent = 'Modo Claro';
        } else {
            themeIcon.className = 'bi bi-moon-stars me-2';
            themeText.textContent = 'Modo Oscuro';
        }
    }

    // Función para aplicar tema
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        updateThemeToggleUI(theme);
        logToBrowserConsole(`🌓 Tema cambiado a: ${theme}`, 'info');
    }

    // Detectar preferencia del sistema operativo si no hay preferencia guardada
    function getInitialTheme() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            return savedTheme;
        }

        // Detectar preferencia del SO
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        return prefersDark ? 'dark' : 'light';
    }

    // Aplicar tema inicial
    const initialTheme = getInitialTheme();
    applyTheme(initialTheme);

    // Event listener para el toggle
    if (themeToggle) {
        themeToggle.addEventListener('click', (e) => {
            e.preventDefault();
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            applyTheme(newTheme);
        });
    }

    // Escuchar cambios en la preferencia del sistema operativo
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        // Solo aplicar si el usuario no ha establecido una preferencia manual
        if (!localStorage.getItem('theme')) {
            const newTheme = e.matches ? 'dark' : 'light';
            applyTheme(newTheme);
        }
    });

    // ===== DENSIDAD DE UI =====
    // Función para aplicar densidad
    function applyDensity(density) {
        document.documentElement.setAttribute('data-density', density);
        localStorage.setItem('ui-density', density);
        logToBrowserConsole(`📏 Densidad de UI cambiada a: ${density}`, 'info');
    }

    // Aplicar densidad inicial (desde localStorage o default)
    const savedDensity = localStorage.getItem('ui-density') || 'compact';
    applyDensity(savedDensity);
    if (densitySelect) {
        densitySelect.value = savedDensity;
    }

    // Event listener para el selector de densidad
    if (densitySelect) {
        densitySelect.addEventListener('change', (e) => {
            applyDensity(e.target.value);
        });
    }

    // =====================================================================
    // SELECTOR DE COLUMNAS - Funciones para optimización de carga
    // =====================================================================

    /**
     * Muestra el modal de selección de columnas
     */
    async function showColumnSelectorModal(blobDisplayName) {
        try {
            // Llamar al endpoint para obtener columnas disponibles
            const response = await fetch(`${API_BASE}/api/data/columns/${encodeURIComponent(blobDisplayName)}`);
            if (!response.ok) {
                throw new Error('No se pudieron obtener las columnas disponibles');
            }

            const data = await response.json();

            // Llenar el modal con las columnas
            populateColumnSelector(data);

            // Mostrar el modal
            const modal = new bootstrap.Modal(document.getElementById('columnSelectorModal'));
            modal.show();

        } catch (error) {
            console.error('Error obteniendo columnas:', error);
            alert('Error al obtener columnas disponibles. Se procederá con todas las columnas.');
            handleDataLoad(); // Fallback a carga normal
        }
    }

    /**
     * Llena el selector con las columnas disponibles
     */
    function populateColumnSelector(data) {
        const essentialContainer = document.getElementById('essential-columns-container');
        const additionalContainer = document.getElementById('additional-columns-container');
        const totalCountSpan = document.getElementById('total-columns-count');

        essentialContainer.innerHTML = '';
        additionalContainer.innerHTML = '';

        const availableColumns = data.available_columns || [];
        const essentialColumns = data.essential_columns || [];
        const defaultSelected = data.default_selected_columns || [];

        totalCountSpan.textContent = availableColumns.length;

        // Columnas esenciales (preseleccionadas)
        essentialColumns.forEach(col => {
            const colDiv = createColumnCheckbox(col, true, true);
            essentialContainer.appendChild(colDiv);
        });

        // Columnas adicionales
        const additionalCols = availableColumns.filter(col => !essentialColumns.includes(col));
        additionalCols.forEach(col => {
            const isSelected = defaultSelected.includes(col);
            const colDiv = createColumnCheckbox(col, isSelected, false);
            additionalContainer.appendChild(colDiv);
        });

        updateColumnSelectionInfo();

        // Configurar búsqueda de columnas
        const searchInput = document.getElementById('column-search-input');
        if (searchInput) {
            searchInput.value = '';
            searchInput.removeEventListener('input', filterColumns);
            searchInput.addEventListener('input', filterColumns);
        }
    }

    /**
     * Crea un checkbox para una columna - versión mejorada con grid
     */
    function createColumnCheckbox(columnName, isChecked, isEssential) {
        const formCheck = document.createElement('div');
        formCheck.className = 'form-check';

        const input = document.createElement('input');
        input.className = 'form-check-input column-checkbox';
        input.type = 'checkbox';
        input.id = `col-${columnName.replace(/\s+/g, '_').replace(/\W/g, '')}`;
        input.value = columnName;
        input.checked = isChecked;
        if (isEssential) {
            input.setAttribute('data-essential', 'true');
        }
        input.addEventListener('change', updateColumnSelectionInfo);

        const label = document.createElement('label');
        label.className = 'form-check-label';
        label.htmlFor = input.id;
        if (isEssential) {
            label.innerHTML = `<i class="bi bi-star-fill text-warning me-1" style="font-size: 0.7rem;"></i>${columnName}`;
        } else {
            label.textContent = columnName;
        }

        formCheck.appendChild(input);
        formCheck.appendChild(label);

        return formCheck;
    }

    /**
     * Actualiza contador de columnas seleccionadas y estimación de RAM
     */
    function updateColumnSelectionInfo() {
        const checkboxes = document.querySelectorAll('.column-checkbox');
        const selectedCount = Array.from(checkboxes).filter(cb => cb.checked).length;

        document.getElementById('selected-columns-count').textContent = selectedCount;

        // Estimación de RAM (aproximado: 2GB para 22 columnas = ~90MB por columna)
        const estimatedGB = (selectedCount / 22 * 2).toFixed(1);
        document.getElementById('estimated-ram').textContent = `~${estimatedGB} GB`;
    }

    /**
     * Filtra columnas según búsqueda - mejorado para grid
     */
    function filterColumns() {
        const searchTerm = document.getElementById('column-search-input').value.toLowerCase();
        const additionalContainer = document.getElementById('additional-columns-container');
        const columnCheckboxes = additionalContainer.querySelectorAll('.form-check');

        columnCheckboxes.forEach(formCheck => {
            const label = formCheck.querySelector('.form-check-label');
            const columnName = label.textContent.toLowerCase();
            formCheck.style.display = columnName.includes(searchTerm) ? '' : 'none';
        });
    }

    /**
     * Selecciona todas las columnas
     */
    window.selectAllColumns = function() {
        document.querySelectorAll('.column-checkbox').forEach(cb => {
            cb.checked = true;
        });
        updateColumnSelectionInfo();
    };

    /**
     * Deselecciona todas las columnas
     */
    window.deselectAllColumns = function() {
        document.querySelectorAll('.column-checkbox').forEach(cb => {
            cb.checked = false;
        });
        updateColumnSelectionInfo();
    };

    /**
     * Restaura columnas predeterminadas (solo esenciales)
     */
    window.restoreDefaultColumns = function() {
        document.querySelectorAll('.column-checkbox').forEach(cb => {
            const isEssential = cb.getAttribute('data-essential') === 'true';
            cb.checked = isEssential;
        });
        updateColumnSelectionInfo();
    };

    /**
     * Confirmar selección y cargar datos
     */
    const confirmColumnSelectionBtn = document.getElementById('confirm-column-selection-btn');
    if (confirmColumnSelectionBtn) {
        confirmColumnSelectionBtn.addEventListener('click', async () => {
            const selectedColumns = Array.from(document.querySelectorAll('.column-checkbox:checked'))
                .map(cb => cb.value);

            if (selectedColumns.length === 0) {
                alert('Debes seleccionar al menos una columna');
                return;
            }

            // Cerrar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('columnSelectorModal'));
            modal.hide();

            // Cargar datos con columnas seleccionadas
            await handleDataLoadWithColumns(selectedColumns);
        });
    }

    /**
     * Carga datos con columnas específicas - Versión completa integrada con handleDataLoad
     */
    async function handleDataLoadWithColumns(selectedColumns) {
        const { currentBlobDisplayName, currentBlobFilename, setAbortController } = getState();

        if (!currentBlobDisplayName) {
            alert('Por favor, selecciona una fuente de datos.');
            return;
        }

        // Cerrar conexión SSE anterior si existe para evitar que añada cards viejas
        if (progressEventSource) {
            progressEventSource.close();
            progressEventSource = null;
            logToBrowserConsole('Conexión SSE anterior cerrada antes de nueva carga', 'debug');
        }

        // Limpiar cards anteriores
        clearEventCards();

        // Limpiar filtros manuales antes de cargar nuevos datos
        clearManualFilterInputs();

        // Limpiar la UI de la tabla antes de empezar la carga
        clearDataTable();

        // Cancelar controlador anterior si existe
        const existingController = getState().abortController;
        if (existingController) {
            try {
                existingController.abort();
            } catch (error) {
                console.warn('Error al abortar controlador anterior:', error);
            }
        }

        const controller = new AbortController();
        setAbortController(controller);

        // Mensaje de carga
        let loadingMessage = `Cargando ${selectedColumns.length} columnas de ${currentBlobDisplayName}...`;
        let submessage = 'Optimizando carga con columnas seleccionadas';

        setState({
            isLoading: true,
            statusMessage: loadingMessage,
            loadingDetails: {
                message: loadingMessage,
                submessage: submessage,
                isProcessing: true
            }
        });

        // Mostrar overlay de carga con cards
        toggleLoadingOverlay(true, loadingMessage, submessage, 0);

        // Actualizar título del overlay
        const loadingTitle = document.getElementById('loading-title');
        if (loadingTitle) {
            loadingTitle.textContent = `Cargando ${selectedColumns.length} columnas de ${currentBlobDisplayName}`;
        }

        // Conectar al SSE de progreso real del backend
        let lastProgressUpdate = Date.now();

        try {
            progressEventSource = new EventSource(`${API_BASE}/api/progress/load/stream`);

            progressEventSource.onmessage = (event) => {
                try {
                    const data = event.data.trim();
                    if (data && data !== 'keep-alive') {
                        const progressData = JSON.parse(data);
                        lastProgressUpdate = Date.now();
                        handleProgressEvent(progressData);
                    }
                } catch (error) {
                    console.error('Error procesando mensaje SSE de progreso:', error);
                }
            };

            progressEventSource.onerror = (error) => {
                console.error('Error en SSE de progreso:', error);
                logToBrowserConsole('Conexión SSE perdida, reintentando...', 'warning');
            };

        } catch (sseError) {
            console.error('Error al crear conexión SSE:', sseError);
            logToBrowserConsole(`Error al conectar SSE: ${sseError.message}`, 'error');
        }

        try {
            // Cargar configuración
            const settingsResponse = await fetchWithRetry(`${API_BASE}/api/config/settings/${currentBlobDisplayName}`, {
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                },
                timeout: 15000
            }, 2, 1500);

            if (!settingsResponse.ok) {
                throw new Error(`Error al cargar configuración: ${settingsResponse.status}`);
            }

            const blobSettings = await settingsResponse.json();
            if (!blobSettings) {
                throw new Error('No se pudo obtener la configuración del servidor');
            }

            setState({
                hiddenColumnsConfig: Array.isArray(blobSettings.hide_columns) ?
                    blobSettings.hide_columns.map(c => String(c).toLowerCase()) :
                    []
            });

            // Cargar datos CON columnas seleccionadas
            const loadResponse = await fetchWithRetry(`${API_BASE}/api/data/load/${currentBlobDisplayName}`, {
                method: 'POST',
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache'
                },
                body: JSON.stringify({
                    selected_columns: selectedColumns
                }),
                timeout: null // Sin timeout automático
            }, 0);

            if (!loadResponse.ok) {
                const errorData = await loadResponse.json().catch(() => ({}));
                throw new Error(errorData.detail || `Error al cargar datos: ${loadResponse.status}`);
            }

            const dataPayload = await loadResponse.json();
            if (!dataPayload) {
                throw new Error('No se recibieron datos del servidor');
            }

            // Validar que tengamos las propiedades necesarias
            if (!Array.isArray(dataPayload.columns)) {
                throw new Error('El formato de datos recibido es inválido (columns)');
            }

            // Crear entrada en caché con las columnas seleccionadas
            dataSourceCache[currentBlobDisplayName] = {
                fileInfo: {
                    displayName: currentBlobDisplayName,
                    fileName: currentBlobFilename,
                    columns: dataPayload.columns.map(c => String(c).toLowerCase()),
                    rowCount: parseInt(dataPayload.row_count_original || 0, 10),
                    cache_ttl_seconds: parseInt(dataPayload.cache_ttl_seconds || 300, 10)
                },
                filterOptions: dataPayload.filter_options || {},
                filterConfig: Array.isArray(blobSettings.filter_columns) ?
                    blobSettings.filter_columns.map(c => c.toLowerCase()) :
                    [],
                ttl: parseInt(dataPayload.cache_ttl_seconds || 300, 10),
                displayData: [],
                filteredRowCount: 0,
                valueFilters: {},
                selectedColumns: [],
                currentPage: 1,
                hasPriorityColumn: false,
                priorityInfo: {}
            };

            // Actualizar indicadores de cache
            updateCacheIndicators();

            logToBrowserConsole(`'${currentBlobDisplayName}' cargado con ${selectedColumns.length} columnas.`);

            // Aplicar filtros iniciales
            await handleApplyFilters(1, true);

            // Actualizar disponibilidad de botones
            updateButtonAvailability();

            // Guardar estado de vista
            setTimeout(() => {
                saveViewState(currentBlobDisplayName);
                logToBrowserConsole(`Estado de vista guardado para '${currentBlobDisplayName}'`, 'debug');
            }, 500);

            // Marcar como completado
            setState({
                isLoading: false,
                loadingDetails: {
                    message: `Carga completada: ${selectedColumns.length} columnas, ${dataPayload.row_count_original || 0} filas`,
                    submessage: '',
                    isProcessing: false
                }
            });

            logToBrowserConsole(`✅ Carga exitosa con ${selectedColumns.length} columnas seleccionadas`, 'success');

        } catch (error) {
            console.error('Error cargando datos con columnas seleccionadas:', error);

            // Verificar si fue cancelación del usuario
            if (error.name === 'AbortError') {
                console.log('Carga de datos cancelada por el usuario');
                setState({
                    statusMessage: 'Carga de datos cancelada.',
                    loadingDetails: {
                        message: 'Carga cancelada',
                        submessage: 'Proceso cancelado por el usuario',
                        isProcessing: false
                    }
                });
            } else {
                setState({
                    isLoading: false,
                    statusMessage: `Error: ${error.message}`,
                    loadingDetails: {
                        message: 'Error al cargar datos',
                        submessage: error.message,
                        isProcessing: false
                    }
                });
                alert(`Error al cargar datos: ${error.message}`);
            }
        } finally {
            // Cerrar conexión SSE al finalizar (éxito o error)
            if (progressEventSource) {
                progressEventSource.close();
                progressEventSource = null;
                logToBrowserConsole('Conexión SSE cerrada al finalizar carga con columnas', 'debug');
            }
        }
    }

    // === INICIALIZACIÓN DE TOOLTIPS ===
    // Inicializar todos los tooltips de Bootstrap al cargar la página
    initializeTooltips();

    // === INICIALIZACIÓN DEL TOUR INTERACTIVO ===
    // Iniciar tour automáticamente si es la primera visita (después de 2 segundos)
    startTourIfFirstVisit(2000);

    // === INICIALIZACIÓN DE QUICK ACTIONS ===
    // Mostrar Quick Actions si no hay datos cargados
    // Se ejecuta después del tour para no interferir
    if (typeof showQuickActionsIfNeeded === 'function') {
        showQuickActionsIfNeeded();
    }
});