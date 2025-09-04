import React from 'react';
import { useNotification, NOTIFICATION_TYPES } from '../contexts/NotificationContext';

const NotificationContainer = () => {
  const { state, actions } = useNotification();

  const getNotificationStyle = (type) => {
    const baseStyle = {
      padding: '12px 16px',
      marginBottom: '8px',
      borderRadius: '8px',
      border: '1px solid',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      animation: 'slideIn 0.3s ease-out',
      maxWidth: '400px',
      wordBreak: 'break-word'
    };

    switch (type) {
      case NOTIFICATION_TYPES.SUCCESS:
        return {
          ...baseStyle,
          backgroundColor: '#d4edda',
          borderColor: '#c3e6cb',
          color: '#155724'
        };
      case NOTIFICATION_TYPES.ERROR:
        return {
          ...baseStyle,
          backgroundColor: '#f8d7da',
          borderColor: '#f5c6cb',
          color: '#721c24'
        };
      case NOTIFICATION_TYPES.WARNING:
        return {
          ...baseStyle,
          backgroundColor: '#fff3cd',
          borderColor: '#ffeaa7',
          color: '#856404'
        };
      case NOTIFICATION_TYPES.INFO:
      default:
        return {
          ...baseStyle,
          backgroundColor: '#d1ecf1',
          borderColor: '#bee5eb',
          color: '#0c5460'
        };
    }
  };

  const getIcon = (type) => {
    switch (type) {
      case NOTIFICATION_TYPES.SUCCESS:
        return '✓';
      case NOTIFICATION_TYPES.ERROR:
        return '✕';
      case NOTIFICATION_TYPES.WARNING:
        return '⚠';
      case NOTIFICATION_TYPES.INFO:
      default:
        return 'ℹ';
    }
  };

  if (state.notifications.length === 0) {
    return null;
  }

  return (
    <div style={{
      position: 'fixed',
      top: '20px',
      right: '20px',
      zIndex: 1000,
      display: 'flex',
      flexDirection: 'column'
    }}>
      <style>
        {`
          @keyframes slideIn {
            from {
              transform: translateX(100%);
              opacity: 0;
            }
            to {
              transform: translateX(0);
              opacity: 1;
            }
          }
        `}
      </style>
      {state.notifications.map((notification) => (
        <div
          key={notification.id}
          style={getNotificationStyle(notification.type)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '16px', fontWeight: 'bold' }}>
              {getIcon(notification.type)}
            </span>
            <span>{notification.message}</span>
          </div>
          <button
            onClick={() => actions.removeNotification(notification.id)}
            style={
              {
                background: 'none',
                border: 'none',
                fontSize: '18px',
                cursor: 'pointer',
                padding: '0',
                marginLeft: '8px',
                opacity: 0.7
              }
            }
            onMouseEnter={(e) => e.target.style.opacity = 1}
            onMouseLeave={(e) => e.target.style.opacity = 0.7}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
};

export default NotificationContainer;