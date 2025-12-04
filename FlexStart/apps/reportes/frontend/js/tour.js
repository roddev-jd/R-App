/**
 * Tour Interactivo para Reportes
 * Guía a nuevos usuarios a través de las funcionalidades principales
 */

// Función para inicializar el tour
export function initTour() {
    // Verificar que Shepherd esté disponible
    if (typeof Shepherd === 'undefined') {
        console.error('Shepherd.js no está cargado');
        return null;
    }

    const tour = new Shepherd.Tour({
        useModalOverlay: true,
        defaultStepOptions: {
            cancelIcon: {
                enabled: true
            },
            classes: 'shepherd-theme-custom',
            scrollTo: { behavior: 'smooth', block: 'center' },
            modalOverlayOpeningPadding: 4,
            modalOverlayOpeningRadius: 8
        }
    });

    // Paso 1: Seleccionar país
    tour.addStep({
        id: 'paso-1-pais',
        title: '<i class="bi bi-flag-fill me-2"></i>Paso 1: Selecciona el País',
        text: `
            <p>Bienvenido a <strong>Reportes</strong>, la plataforma de análisis de datos para Publicación y Contenido.</p>
            <p>Comienza seleccionando el <strong>país</strong> de la fuente de datos que deseas consultar.</p>
            <p class="mb-0"><small class="text-muted"><i class="bi bi-lightbulb-fill me-1"></i>Puedes elegir entre Chile o Perú</small></p>
        `,
        attachTo: {
            element: '#country-select',
            on: 'bottom'
        },
        buttons: [
            {
                text: 'Salir',
                classes: 'btn btn-sm btn-secondary',
                action: tour.cancel
            },
            {
                text: 'Siguiente',
                classes: 'btn btn-sm btn-primary',
                action: tour.next
            }
        ]
    });

    // Paso 2: Seleccionar fuente de datos
    tour.addStep({
        id: 'paso-2-fuente',
        title: '<i class="bi bi-database-fill me-2"></i>Paso 2: Elige la Fuente de Datos',
        text: `
            <p>Ahora selecciona la <strong>fuente de datos específica</strong> que deseas analizar.</p>
            <p>Cada fuente contiene diferentes tipos de información:</p>
            <ul class="small mb-2">
                <li><strong>Universo Chile/Perú:</strong> Datos completos de WOP</li>
                <li><strong>Diseño/Redacción Perú:</strong> Datos específicos de equipo</li>
            </ul>
            <p class="mb-0"><small class="text-muted"><i class="bi bi-lightbulb-fill me-1"></i>Las fuentes de SharePoint requieren autenticación</small></p>
        `,
        attachTo: {
            element: '#blob-select',
            on: 'bottom'
        },
        buttons: [
            {
                text: 'Anterior',
                classes: 'btn btn-sm btn-secondary',
                action: tour.back
            },
            {
                text: 'Siguiente',
                classes: 'btn btn-sm btn-primary',
                action: tour.next
            }
        ]
    });

    // Paso 3: Cargar datos
    tour.addStep({
        id: 'paso-3-cargar',
        title: '<i class="bi bi-cloud-download-fill me-2"></i>Paso 3: Carga los Datos',
        text: `
            <p>Una vez seleccionada la fuente, haz clic en <strong>"Cargar Datos"</strong>.</p>
            <p>El sistema usa <strong>caché inteligente automático</strong> que:</p>
            <ul class="small mb-2">
                <li><strong>Verifica automáticamente</strong> si hay actualizaciones en el servidor</li>
                <li><strong>Usa caché</strong> si los datos están actualizados <span style="color: #10b981;">●</span></li>
                <li><strong>Descarga</strong> nueva versión si hay cambios <span style="color: #3b82f6;">●</span></li>
            </ul>
            <p class="mb-0"><small class="text-muted"><i class="bi bi-lightbulb-fill me-1"></i>Verás un indicador de color mostrando si usa caché (verde) o descarga (azul)</small></p>
        `,
        attachTo: {
            element: '#load-data-btn',
            on: 'bottom'
        },
        buttons: [
            {
                text: 'Anterior',
                classes: 'btn btn-sm btn-secondary',
                action: tour.back
            },
            {
                text: 'Siguiente',
                classes: 'btn btn-sm btn-primary',
                action: tour.next
            }
        ]
    });

    // Paso 4: Aplicar filtros
    tour.addStep({
        id: 'paso-4-filtros',
        title: '<i class="bi bi-funnel-fill me-2"></i>Paso 4: Filtra los Datos',
        text: `
            <p>Usa el <strong>panel de filtros</strong> para refinar tus resultados.</p>
            <p>Puedes filtrar por:</p>
            <ul class="small mb-2">
                <li><strong>Filtros:</strong> Valores de columnas específicas</li>
                <li><strong>Códigos:</strong> SKU hijo, SKU padre, tickets</li>
                <li><strong>Columnas:</strong> Selecciona qué columnas mostrar</li>
            </ul>
            <p>Después de configurar, haz clic en <strong>"Aplicar Filtros"</strong> al final del panel.</p>
            <p class="mb-0"><small class="text-muted"><i class="bi bi-lightbulb-fill me-1"></i>Puedes guardar tus filtros como favorito</small></p>
        `,
        attachTo: {
            element: '#left-panel',
            on: 'right'
        },
        buttons: [
            {
                text: 'Anterior',
                classes: 'btn btn-sm btn-secondary',
                action: tour.back
            },
            {
                text: 'Siguiente',
                classes: 'btn btn-sm btn-primary',
                action: tour.next
            }
        ]
    });

    // Paso 5: Exportar resultados
    tour.addStep({
        id: 'paso-5-exportar',
        title: '<i class="bi bi-file-earmark-excel-fill me-2"></i>Paso 5: Exporta tus Resultados',
        text: `
            <p>Finalmente, puedes exportar los datos filtrados en dos formatos:</p>
            <ul class="small mb-2">
                <li><strong>Excel:</strong> Archivo con formato y colores por prioridad</li>
                <li><strong>CSV:</strong> Archivo simple para procesamiento adicional</li>
            </ul>
            <p>También puedes activar el <strong>coloreado por prioridad</strong> en las opciones de tabla.</p>
            <p class="mb-0"><strong>¡Eso es todo! Ya estás listo para usar Reportes.</strong></p>
            <p class="mb-0 mt-2"><small class="text-muted"><i class="bi bi-info-circle-fill me-1"></i>Puedes volver a ver este tutorial desde el menú de opciones (⋮)</small></p>
        `,
        attachTo: {
            element: '#export-excel-button',
            on: 'bottom'
        },
        buttons: [
            {
                text: 'Anterior',
                classes: 'btn btn-sm btn-secondary',
                action: tour.back
            },
            {
                text: '¡Entendido!',
                classes: 'btn btn-sm btn-success',
                action: tour.complete
            }
        ]
    });

    // Eventos del tour
    tour.on('complete', () => {
        localStorage.setItem('reportes_tour_completed', 'true');
        console.log('✓ Tour completado');
    });

    tour.on('cancel', () => {
        console.log('Tour cancelado por el usuario');
    });

    return tour;
}

// Función para verificar si es la primera visita
export function isFirstVisit() {
    return !localStorage.getItem('reportes_tour_completed');
}

// Función para reiniciar el tour (marcar como no visto)
export function resetTour() {
    localStorage.removeItem('reportes_tour_completed');
}

// Función para iniciar el tour automáticamente si es primera visita
export function startTourIfFirstVisit(delay = 1500) {
    if (isFirstVisit()) {
        setTimeout(() => {
            const tour = initTour();
            if (tour) {
                tour.start();
                console.log('→ Iniciando tour para nuevo usuario');
            }
        }, delay);
    }
}

// Función para iniciar el tour manualmente
export function startTour() {
    const tour = initTour();
    if (tour) {
        tour.start();
        console.log('→ Tour iniciado manualmente');
    }
}
