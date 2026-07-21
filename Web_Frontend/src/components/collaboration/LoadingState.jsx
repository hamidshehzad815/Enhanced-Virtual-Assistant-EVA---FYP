import React from 'react';
import { Loader } from 'lucide-react';
import './LoadingState.css';

/**
 * LoadingState
 * Displays loading indicators during collaboration operations
 * Types: creating, sending, checking, scheduling, updating
 */
export const LoadingState = ({ 
  type = 'general', 
  message = null,
  size = 'md'
}) => {
  const messages = {
    creating: 'Creating task...',
    sending: 'Sending invitations...',
    checking: 'Checking collaborator availability...',
    scheduling: 'Finding available times...',
    updating: 'Updating collaboration status...',
    general: 'Processing...',
  };

  const displayMessage = message || messages[type] || messages.general;

  return (
    <div className={`loading-state ${size}`}>
      <div className="loading-spinner">
        <Loader size={size === 'sm' ? 14 : size === 'lg' ? 24 : 18} />
      </div>
      <span className="loading-text">{displayMessage}</span>
    </div>
  );
};

export default LoadingState;
