/**
 * Favorites Manager - Sistema basado en backend con favoritos separados por base de datos
 * Guarda y carga el estado de filtros y columnas en config.ini del servidor
 * Cada base de datos tiene su propio favorito independiente
 */

// API Base path para reportes
const API_BASE = '/reportes';

/**
 * Guarda el estado actual como favorito en el backend para una base de datos específica
 * @param {Object} state - Estado a guardar {value_filters, selected_columns, extend_sku_search}
 * @param {string} databaseName - Nombre de la base de datos (ej: "Chile_Wop", "Peru_Staff")
 * @returns {Promise<boolean>} - true si se guardó exitosamente
 */
export async function saveFavorite(state, databaseName) {
    try {
        if (!state || typeof state !== 'object') {
            console.error('Estado inválido para guardar');
            return false;
        }

        if (!databaseName) {
            console.error('databaseName es requerido');
            return false;
        }

        // Agregar database_name al payload
        const payload = {
            ...state,
            database_name: databaseName
        };

        const response = await fetch(`${API_BASE}/api/favorites/save`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        return result.status === 'success';
    } catch (error) {
        console.error('Error al guardar favorito:', error);
        return false;
    }
}

/**
 * Carga el favorito guardado desde el backend para una base de datos específica
 * @param {string} databaseName - Nombre de la base de datos (ej: "Chile_Wop", "Peru_Staff")
 * @returns {Promise<Object|null>} - Estado guardado con metadata o null si no existe
 */
export async function loadFavorite(databaseName) {
    try {
        if (!databaseName) {
            console.error('databaseName es requerido');
            return null;
        }

        const response = await fetch(`${API_BASE}/api/favorites/load/${encodeURIComponent(databaseName)}`, {
            method: 'GET'
        });

        if (response.status === 404) {
            return null; // No hay favorito guardado para esta base
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        return result.status === 'success' ? result.data : null;
    } catch (error) {
        console.error('Error al cargar favorito:', error);
        return null;
    }
}

/**
 * Verifica si existe un favorito guardado en el backend para una base de datos específica
 * @param {string} databaseName - Nombre de la base de datos (ej: "Chile_Wop", "Peru_Staff")
 * @returns {Promise<Object|null>} - Metadata del favorito {exists, database_name, timestamp} o null
 */
export async function hasFavorite(databaseName) {
    try {
        if (!databaseName) {
            console.error('databaseName es requerido');
            return null;
        }

        const response = await fetch(`${API_BASE}/api/favorites/has/${encodeURIComponent(databaseName)}`, {
            method: 'GET'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        return result.status === 'success' ? result.data : null;
    } catch (error) {
        console.error('Error al verificar favorito:', error);
        return null;
    }
}

/**
 * Elimina el favorito guardado del backend para una base de datos específica
 * @param {string} databaseName - Nombre de la base de datos (ej: "Chile_Wop", "Peru_Staff")
 * @returns {Promise<boolean>} - true si se eliminó
 */
export async function deleteFavorite(databaseName) {
    try {
        if (!databaseName) {
            console.error('databaseName es requerido');
            return false;
        }

        const response = await fetch(`${API_BASE}/api/favorites/delete/${encodeURIComponent(databaseName)}`, {
            method: 'DELETE'
        });

        if (response.status === 404) {
            return false; // No había favorito para esta base
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        return result.status === 'success';
    } catch (error) {
        console.error('Error al eliminar favorito:', error);
        return false;
    }
}
