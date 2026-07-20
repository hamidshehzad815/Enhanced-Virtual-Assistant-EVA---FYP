import React from 'react';
import { StatusIndicator } from './StatusIndicator';
import './CollaboratorsList.css';

/**
 * CollaboratorsList
 * Displays a list of collaborators with their individual status
 * Each collaborator shows name, status, and optional action buttons
 */
export const CollaboratorsList = ({ 
  collaborators = [], 
  onRemove = null,
  onResend = null,
  maxDisplay = null,
  compact = false
}) => {
  if (!collaborators || collaborators.length === 0) {
    return (
      <div className="collaborators-list empty">
        <p>No collaborators added yet</p>
      </div>
    );
  }

  const displayCollaborators = maxDisplay 
    ? collaborators.slice(0, maxDisplay) 
    : collaborators;
  const remainingCount = maxDisplay 
    ? Math.max(0, collaborators.length - maxDisplay) 
    : 0;

  return (
    <div className={`collaborators-list ${compact ? 'compact' : ''}`}>
      {displayCollaborators.map((collaborator, idx) => {
        const status = collaborator.status || 'pending';
        const name = collaborator.name || collaborator.username || 'Unknown';
        const id = collaborator._id || collaborator.id || idx;

        return (
          <div key={id} className="collaborator-row">
            <div className="collaborator-info">
              <div className="collaborator-avatar">
                {name.charAt(0).toUpperCase()}
              </div>
              <div className="collaborator-details">
                <span className="collaborator-name">{name}</span>
                {collaborator.email && (
                  <span className="collaborator-email">{collaborator.email}</span>
                )}
              </div>
            </div>

            <div className="collaborator-status">
              <StatusIndicator status={status} size="sm" showLabel={true} />
            </div>

            {(onRemove || onResend) && status !== 'accepted' && (
              <div className="collaborator-actions">
                {onResend && status === 'pending' && (
                  <button 
                    className="action-btn resend-btn"
                    onClick={() => onResend(id)}
                    title="Resend invitation"
                  >
                    Resend
                  </button>
                )}
                {onRemove && (
                  <button 
                    className="action-btn remove-btn"
                    onClick={() => onRemove(id)}
                    title="Remove collaborator"
                  >
                    Remove
                  </button>
                )}
              </div>
            )}
          </div>
        );
      })}

      {remainingCount > 0 && (
        <div className="collaborators-more">
          <span>+{remainingCount} more collaborator{remainingCount !== 1 ? 's' : ''}</span>
        </div>
      )}
    </div>
  );
};

export default CollaboratorsList;
