import { createStore } from './zustand-vanilla.mjs';

const appStore = createStore((set, get) => ({
  isLoading: false,
  statusMessage: 'Listo. Seleccione una fuente de datos.',
  loadingDetails: {
    message: '',
    submessage: '',
    isProcessing: false
  },
  currentBlobDisplayName: null,
  currentBlobFilename: null,
  originalDataColumns: [],
  hiddenColumnsConfig: [],
  dataForDisplay: [],
  rowCount: { original: 0, filtered: 0, display: 0 },
  skuHijoFileLoaded: false,
  skuPadreFileLoaded: false,
  abortController: null,

  setLoading: (loading, message, submessage = '') => {
    const state = { 
      isLoading: loading,
      loadingDetails: {
        message: message || 'Procesando...',
        submessage: submessage,
        isProcessing: loading
      }
    };
    if (message) {
      state.statusMessage = message;
    }
    set(state);
  },

  setStatus: (message) => set({ statusMessage: message }),

  resetForNewFile: () => set({
    currentBlobDisplayName: null,
    currentBlobFilename: null,
    originalDataColumns: [],
    dataForDisplay: [],
    hiddenColumnsConfig: [],
    rowCount: { original: 0, filtered: 0, display: 0 },
    skuHijoFileLoaded: false,
    skuPadreFileLoaded: false,
    loadingDetails: {
      message: '',
      submessage: '',
      isProcessing: false
    }
  }),

  setFileLoaded: (payload) => set({
    currentBlobDisplayName: payload.displayName,
    currentBlobFilename: payload.fileName,
    originalDataColumns: payload.columns,
    rowCount: { ...get().rowCount, original: payload.rowCount },
    statusMessage: `Archivo '${payload.displayName}' cargado con ${payload.rowCount} filas.`,
    loadingDetails: {
      message: '',
      submessage: '',
      isProcessing: false
    }
  }),

  setDisplayData: (data, filteredCount) => set(state => ({
    dataForDisplay: data,
    rowCount: { ...state.rowCount, display: data.length, filtered: filteredCount },
    statusMessage: `Mostrando ${data.length} de ${filteredCount} filas filtradas.`,
    loadingDetails: {
      message: '',
      submessage: '',
      isProcessing: false
    }
  })),

  setAbortController: (controller) => set({ abortController: controller }),
}));

export { appStore };