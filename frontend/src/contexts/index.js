// Exportaciones centralizadas de contextos
export { AppProvider, useApp, APP_ACTIONS } from './AppContext';
export { NotificationProvider, useNotification, NOTIFICATION_TYPES, NOTIFICATION_ACTIONS } from './NotificationContext';

// Exportación de un provider combinado para facilitar el uso
import React from 'react';
import { AppProvider } from './AppContext';
import { NotificationProvider } from './NotificationContext';

export const CombinedProvider = ({ children }) => {
  return (
    <NotificationProvider>
      <AppProvider>
        {children}
      </AppProvider>
    </NotificationProvider>
  );
};

export default {
  AppProvider,
  NotificationProvider,
  CombinedProvider,
  useApp,
  useNotification,
  APP_ACTIONS,
  NOTIFICATION_TYPES,
  NOTIFICATION_ACTIONS
};