import React, { createContext, useContext, useReducer } from 'react';

// Estado inicial
const initialState = {
  notifications: []
};

// Tipos de notificaciones
export const NOTIFICATION_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info'
};

// Tipos de acciones
export const NOTIFICATION_ACTIONS = {
  ADD_NOTIFICATION: 'ADD_NOTIFICATION',
  REMOVE_NOTIFICATION: 'REMOVE_NOTIFICATION',
  CLEAR_NOTIFICATIONS: 'CLEAR_NOTIFICATIONS'
};

// Reducer
const notificationReducer = (state, action) => {
  switch (action.type) {
    case NOTIFICATION_ACTIONS.ADD_NOTIFICATION:
      return {
        ...state,
        notifications: [...state.notifications, action.payload]
      };
    case NOTIFICATION_ACTIONS.REMOVE_NOTIFICATION:
      return {
        ...state,
        notifications: state.notifications.filter(n => n.id !== action.payload)
      };
    case NOTIFICATION_ACTIONS.CLEAR_NOTIFICATIONS:
      return {
        ...state,
        notifications: []
      };
    default:
      return state;
  }
};

// Contexto
const NotificationContext = createContext();

// Provider
export const NotificationProvider = ({ children }) => {
  const [state, dispatch] = useReducer(notificationReducer, initialState);

  // Función para generar ID único
  const generateId = () => Date.now() + Math.random();

  // Acciones
  const actions = {
    addNotification: (message, type = NOTIFICATION_TYPES.INFO, duration = 5000) => {
      const id = generateId();
      const notification = {
        id,
        message,
        type,
        timestamp: new Date().toISOString()
      };
      
      dispatch({ type: NOTIFICATION_ACTIONS.ADD_NOTIFICATION, payload: notification });
      
      // Auto-remover después del tiempo especificado
      if (duration > 0) {
        setTimeout(() => {
          dispatch({ type: NOTIFICATION_ACTIONS.REMOVE_NOTIFICATION, payload: id });
        }, duration);
      }
      
      return id;
    },
    
    removeNotification: (id) => {
      dispatch({ type: NOTIFICATION_ACTIONS.REMOVE_NOTIFICATION, payload: id });
    },
    
    clearNotifications: () => {
      dispatch({ type: NOTIFICATION_ACTIONS.CLEAR_NOTIFICATIONS });
    },
    
    // Métodos de conveniencia
    showSuccess: (message, duration) => actions.addNotification(message, NOTIFICATION_TYPES.SUCCESS, duration),
    showError: (message, duration) => actions.addNotification(message, NOTIFICATION_TYPES.ERROR, duration),
    showWarning: (message, duration) => actions.addNotification(message, NOTIFICATION_TYPES.WARNING, duration),
    showInfo: (message, duration) => actions.addNotification(message, NOTIFICATION_TYPES.INFO, duration)
  };

  return (
    <NotificationContext.Provider value={{ state, actions }}>
      {children}
    </NotificationContext.Provider>
  );
};

// Hook personalizado
export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification debe ser usado dentro de NotificationProvider');
  }
  return context;
};

export default NotificationContext;