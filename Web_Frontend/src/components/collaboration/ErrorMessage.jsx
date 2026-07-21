import React from 'react';
import { AlertTriangle, X } from 'lucide-react';
import './ErrorMessage.css';

/**
 * ErrorMessage
 * Displays backend error messages in a clear and readable format
 * Errors are displayed exactly as received from the backend
 */
export const ErrorMessage = ({ 
  message = 'An error occurred', 
  title = 'Error',
  type = 'error',
  onDismiss = null,
  dismissible = true,
  details = null
}) => {
  const getErrorConfig = (type) => {
    switch (type?.toLowerCase()) {
      case 'conflict':
        return {
          className: 'error-message-conflict',
          icon: AlertTriangle,
          bgClass: 'bg-error-conflict',
          borderClass: 'border-error-conflict',
          iconClass: 'icon-conflict',
        };
      case 'warning':
        return {
          className: 'error-message-warning',
          icon: AlertTriangle,
          bgClass: 'bg-error-warning',
          borderClass: 'border-error-warning',
          iconClass: 'icon-warning',
        };
      case 'info':
        return {
          className: 'error-message-info',
          icon: AlertTriangle,
          bgClass: 'bg-error-info',
          borderClass: 'border-error-info',
          iconClass: 'icon-info',
        };
      case 'error':
      default:
        return {
          className: 'error-message-error',
          icon: AlertTriangle,
          bgClass: 'bg-error-error',
          borderClass: 'border-error-error',
          iconClass: 'icon-error',
        };
    }
  };

  const config = getErrorConfig(type);
  const IconComponent = config.icon;

  return (
    <div className={`error-message ${config.className}`}>
      <div className="error-icon">
        <IconComponent size={16} />
      </div>

      <div className="error-content">
        {title && <h4 className="error-title">{title}</h4>}
        <p className="error-message-text">{message}</p>
        {details && (
          <div className="error-details">
            {typeof details === 'string' ? (
              <p>{details}</p>
            ) : (
              Object.entries(details).map(([key, value]) => (
                <div key={key} className="detail-row">
                  <span className="detail-key">{key}:</span>
                  <span className="detail-value">{String(value)}</span>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {dismissible && onDismiss && (
        <button 
          className="error-dismiss-btn"
          onClick={onDismiss}
          title="Dismiss"
          aria-label="Dismiss error"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
};

export default ErrorMessage;
