import React, { createContext, useContext, useReducer } from 'react';

// Estado inicial
const initialState = {
  jobId: null,
  jobStatus: 'idle', // 'idle', 'processing', 'completed', 'error'
  results: null,
  loading: false,
  error: null,
  selectedFile: null,
  youtubeUrl: '',
  activeOption: 0
};

// Tipos de acciones
export const APP_ACTIONS = {
  SET_JOB_ID: 'SET_JOB_ID',
  SET_JOB_STATUS: 'SET_JOB_STATUS',
  SET_RESULTS: 'SET_RESULTS',
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  SET_SELECTED_FILE: 'SET_SELECTED_FILE',
  SET_YOUTUBE_URL: 'SET_YOUTUBE_URL',
  SET_ACTIVE_OPTION: 'SET_ACTIVE_OPTION',
  RESET_STATE: 'RESET_STATE'
};

// Reducer
const appReducer = (state, action) => {
  switch (action.type) {
    case APP_ACTIONS.SET_JOB_ID:
      return { ...state, jobId: action.payload };
    case APP_ACTIONS.SET_JOB_STATUS:
      return { ...state, jobStatus: action.payload };
    case APP_ACTIONS.SET_RESULTS:
      return { ...state, results: action.payload };
    case APP_ACTIONS.SET_LOADING:
      return { ...state, loading: action.payload };
    case APP_ACTIONS.SET_ERROR:
      return { ...state, error: action.payload };
    case APP_ACTIONS.SET_SELECTED_FILE:
      return { ...state, selectedFile: action.payload };
    case APP_ACTIONS.SET_YOUTUBE_URL:
      return { ...state, youtubeUrl: action.payload };
    case APP_ACTIONS.SET_ACTIVE_OPTION:
      return { ...state, activeOption: action.payload };
    case APP_ACTIONS.RESET_STATE:
      return { ...initialState, activeOption: state.activeOption };
    default:
      return state;
  }
};

// Contexto
const AppContext = createContext();

// Provider
export const AppProvider = ({ children }) => {
  const [state, dispatch] = useReducer(appReducer, initialState);

  // Acciones
  const actions = {
    setJobId: (jobId) => dispatch({ type: APP_ACTIONS.SET_JOB_ID, payload: jobId }),
    setJobStatus: (status) => dispatch({ type: APP_ACTIONS.SET_JOB_STATUS, payload: status }),
    setResults: (results) => dispatch({ type: APP_ACTIONS.SET_RESULTS, payload: results }),
    setLoading: (loading) => dispatch({ type: APP_ACTIONS.SET_LOADING, payload: loading }),
    setError: (error) => dispatch({ type: APP_ACTIONS.SET_ERROR, payload: error }),
    setSelectedFile: (file) => dispatch({ type: APP_ACTIONS.SET_SELECTED_FILE, payload: file }),
    setYoutubeUrl: (url) => dispatch({ type: APP_ACTIONS.SET_YOUTUBE_URL, payload: url }),
    setActiveOption: (option) => dispatch({ type: APP_ACTIONS.SET_ACTIVE_OPTION, payload: option }),
    resetState: () => dispatch({ type: APP_ACTIONS.RESET_STATE })
  };

  return (
    <AppContext.Provider value={{ state, actions }}>
      {children}
    </AppContext.Provider>
  );
};

// Hook personalizado
export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp debe ser usado dentro de AppProvider');
  }
  return context;
};

export default AppContext;