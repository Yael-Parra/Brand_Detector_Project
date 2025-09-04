import React from 'react';

const LoadingSpinner = ({ 
  size = 'medium', 
  message = 'Cargando...', 
  showMessage = true,
  color = '#007bff'
}) => {
  const getSizeStyles = () => {
    switch (size) {
      case 'small':
        return { width: '20px', height: '20px', borderWidth: '2px' };
      case 'large':
        return { width: '60px', height: '60px', borderWidth: '4px' };
      case 'medium':
      default:
        return { width: '40px', height: '40px', borderWidth: '3px' };
    }
  };

  const sizeStyles = getSizeStyles();

  const spinnerStyles = {
    ...sizeStyles,
    border: `${sizeStyles.borderWidth} solid #f3f3f3`,
    borderTop: `${sizeStyles.borderWidth} solid ${color}`,
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    margin: showMessage ? '0 auto 1rem auto' : '0 auto'
  };

  const containerStyles = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '1rem'
  };

  const messageStyles = {
    color: '#6c757d',
    fontSize: size === 'small' ? '0.8rem' : size === 'large' ? '1.1rem' : '1rem',
    fontWeight: '500',
    textAlign: 'center'
  };

  return (
    <>
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
      <div style={containerStyles}>
        <div style={spinnerStyles}></div>
        {showMessage && <div style={messageStyles}>{message}</div>}
      </div>
    </>
  );
};

// Componente de overlay de loading para pantalla completa
export const LoadingOverlay = ({ 
  isVisible = false, 
  message = 'Procesando...', 
  backgroundColor = 'rgba(0, 0, 0, 0.5)' 
}) => {
  if (!isVisible) return null;

  const overlayStyles = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999
  };

  const contentStyles = {
    backgroundColor: 'white',
    padding: '2rem',
    borderRadius: '8px',
    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
    textAlign: 'center',
    minWidth: '200px'
  };

  return (
    <div style={overlayStyles}>
      <div style={contentStyles}>
        <LoadingSpinner size="large" message={message} color="#007bff" />
      </div>
    </div>
  );
};

// Componente de loading inline para botones
export const ButtonSpinner = ({ size = 'small', color = 'white' }) => {
  return (
    <LoadingSpinner 
      size={size} 
      showMessage={false} 
      color={color}
    />
  );
};

export default LoadingSpinner;