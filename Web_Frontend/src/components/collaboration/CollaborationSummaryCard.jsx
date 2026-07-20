import React from 'react';
import { Calendar, Clock, User, Users, ChevronDown } from 'lucide-react';
import { CollaboratorsList } from './CollaboratorsList';
import { StatusIndicator } from './StatusIndicator';
import './CollaborationSummaryCard.css';

/**
 * CollaborationSummaryCard
 * Displays a summary of task details with collaboration information
 * Shows task title, date, time, owner, collaborators, and status
 */
export const CollaborationSummaryCard = ({ 
  task = {},
  collaborationStatus = null,
  collaborators = [],
  expandable = true,
  defaultExpanded = false,
  showOwner = true,
  maxDisplayCollaborators = 3
}) => {
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded);

  const taskTitle = task.title || task.name || 'Untitled Task';
  const dueDate = task.due_date || task.due_datetime || task.date;
  const duration = task.duration || 120;
  const owner = task.owner || task.created_by;
  const ownerName = owner?.name || owner?.username || 'You';

  const formatDate = (dateString) => {
    if (!dateString) return null;
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString([], { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric'
      });
    } catch {
      return dateString;
    }
  };

  const formatTime = (dateString) => {
    if (!dateString) return null;
    try {
      const date = new Date(dateString);
      return date.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true
      });
    } catch {
      return dateString;
    }
  };

  const formattedDate = formatDate(dueDate);
  const formattedTime = formatTime(dueDate);

  const displayCollaborators = collaborators.slice(0, maxDisplayCollaborators);
  const moreCount = Math.max(0, collaborators.length - maxDisplayCollaborators);

  return (
    <div className={`collaboration-summary-card ${isExpanded && expandable ? 'expanded' : ''}`}>
      <div className="card-header">
        <div className="card-title-section">
          <div className="card-title-with-icon">
            <span className="task-title">{taskTitle}</span>
            {collaborationStatus && (
              <StatusIndicator 
                status={collaborationStatus} 
                size="sm" 
                showLabel={true}
              />
            )}
          </div>
        </div>

        {expandable && collaborators.length > 0 && (
          <button 
            className="expand-btn"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Collapse' : 'Expand'}
          >
            <ChevronDown size={16} className={isExpanded ? 'rotated' : ''} />
          </button>
        )}
      </div>

      <div className="card-details">
        {formattedDate && (
          <div className="detail-row">
            <Calendar size={14} className="detail-icon" />
            <span className="detail-label">{formattedDate}</span>
            {formattedTime && (
              <>
                <Clock size={14} className="detail-icon time-icon" />
                <span className="detail-label">{formattedTime}</span>
              </>
            )}
          </div>
        )}

        {showOwner && ownerName && (
          <div className="detail-row">
            <User size={14} className="detail-icon" />
            <span className="detail-label">Owner: <strong>{ownerName}</strong></span>
          </div>
        )}
      </div>

      {collaborators.length > 0 && (
        <div className={`collaborators-section ${isExpanded && expandable ? 'expanded-section' : ''}`}>
          <div className="collaborators-header">
            <Users size={14} />
            <span className="collaborators-count">
              {collaborators.length} collaborator{collaborators.length !== 1 ? 's' : ''}
            </span>
          </div>

          {(!expandable || isExpanded) && (
            <CollaboratorsList 
              collaborators={collaborators}
              compact={true}
            />
          )}

          {expandable && !isExpanded && displayCollaborators.length > 0 && (
            <div className="collaborators-preview">
              {displayCollaborators.map((collab, idx) => (
                <div key={idx} className="collab-avatar-mini">
                  {(collab.name || collab.username || 'U').charAt(0).toUpperCase()}
                </div>
              ))}
              {moreCount > 0 && (
                <div className="collab-avatar-mini more">
                  +{moreCount}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CollaborationSummaryCard;
