import React, { useState } from 'react';
import { AlertCircle, CheckCircle, Clock, Users, Calendar } from 'lucide-react';
import { CollaborationSummaryCard } from './CollaborationSummaryCard';
import { CollaboratorsList } from './CollaboratorsList';
import { SuggestedTimeSlots } from './SuggestedTimeSlots';
import { StatusIndicator } from './StatusIndicator';
import { ErrorMessage } from './ErrorMessage';
import './CollaborationMessage.css';

/**
 * CollaborationMessage
 * Renders collaboration-related responses from the AI
 * Types: task_created, invite_sent, invite_accepted, invite_rejected, conflict, status_update
 */
export const CollaborationMessage = ({ 
  data = {},
  onSelectTimeSlot = null,
  messageType = 'general'
}) => {
  const [isLoading, setIsLoading] = useState(false);

  // Helper to determine the type of collaboration message
  const getMessageType = () => {
    if (data.type) return data.type;
    
    // Check for error messages
    if (data.error || data.error_message || data.is_error) return 'error';
    
    if (data.suggested_times && data.suggested_times.length > 0) return 'conflict';
    if (data.task_created) return 'task_created';
    if (data.invites_sent) return 'invite_sent';
    if (data.collaboration_status) return 'status_update';
    if (data.collaborators) return 'collaborators_list';
    
    return null;
  };

  const msgType = getMessageType();

  if (!msgType) return null;

  const handleSelectTimeSlot = async (slot) => {
    setIsLoading(true);
    try {
      if (onSelectTimeSlot) {
        await onSelectTimeSlot(slot);
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Task Created
  if (msgType === 'task_created' && data.task_created) {
    const task = data.task_created;
    return (
      <div className="collaboration-message task-created">
        <div className="msg-header">
          <CheckCircle size={18} className="success-icon" />
          <span className="msg-title">Task Created Successfully</span>
        </div>
        <CollaborationSummaryCard 
          task={task}
          showOwner={true}
        />
        {task.collaborators && task.collaborators.length > 0 && (
          <div className="collab-section">
            <h5>Collaborators</h5>
            <CollaboratorsList collaborators={task.collaborators} />
          </div>
        )}
      </div>
    );
  }

  // Invite Sent
  if (msgType === 'invite_sent' && data.invites_sent) {
    const invites = Array.isArray(data.invites_sent) ? data.invites_sent : [data.invites_sent];
    const task = data.task || {};
    
    return (
      <div className="collaboration-message invite-sent">
        <div className="msg-header">
          <Users size={18} className="info-icon" />
          <span className="msg-title">Collaboration Invites Sent</span>
        </div>
        {(task.title || task.name) && (
          <CollaborationSummaryCard 
            task={task}
            collaborators={invites}
            collaborationStatus="pending"
          />
        )}
        <div className="invites-summary">
          <p>{invites.length} invitation{invites.length !== 1 ? 's' : ''} sent to collaborators</p>
          <CollaboratorsList 
            collaborators={invites}
            compact={true}
          />
        </div>
      </div>
    );
  }

  // Scheduling Conflict with Suggested Times
  if (msgType === 'conflict' && data.suggested_times) {
    const conflictMsg = data.conflict_message || 'Scheduling conflict detected';
    const task = data.task || { title: 'Task' };
    
    return (
      <div className="collaboration-message scheduling-conflict">
        <div className="msg-header error">
          <AlertCircle size={18} className="error-icon" />
          <span className="msg-title">Scheduling Conflict</span>
        </div>
        
        <p className="conflict-detail">{conflictMsg}</p>

        {task && (
          <CollaborationSummaryCard 
            task={task}
            collaborators={data.collaborators || []}
          />
        )}

        <SuggestedTimeSlots 
          slots={data.suggested_times}
          taskTitle={task.title}
          onSelectSlot={handleSelectTimeSlot}
          isLoading={isLoading}
        />
      </div>
    );
  }

  // Collaboration Status Update
  if (msgType === 'status_update' && data.collaboration_status) {
    const status = data.collaboration_status;
    const task = data.task || {};
    
    return (
      <div className="collaboration-message status-update">
        <div className="msg-header">
          <Clock size={18} className="info-icon" />
          <span className="msg-title">Collaboration Status Update</span>
        </div>

        {(task.title || task.name) && (
          <CollaborationSummaryCard 
            task={task}
            collaborators={status.collaborators || []}
            collaborationStatus={status.status}
          />
        )}

        {status.message && (
          <p className="status-message">{status.message}</p>
        )}

        {status.updates && status.updates.length > 0 && (
          <div className="status-updates">
            {status.updates.map((update, idx) => (
              <div key={idx} className="status-update-row">
                <StatusIndicator status={update.status} size="sm" />
                <span className="update-name">{update.name || update.username}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Collaborators List
  if (msgType === 'collaborators_list' && data.collaborators) {
    return (
      <div className="collaboration-message collaborators-list-msg">
        <div className="msg-header">
          <Users size={18} className="info-icon" />
          <span className="msg-title">Collaborators</span>
        </div>
        <CollaboratorsList collaborators={data.collaborators} />
      </div>
    );
  }

  // Error Message
  if (msgType === 'error') {
    const errorMessage = data.error || data.error_message || data.message || 'An error occurred';
    const errorType = data.error_type || 'error';
    
    // Determine if it's a conflict error
    let messageType = 'error';
    if (data.conflict || errorType.toLowerCase().includes('conflict')) {
      messageType = 'conflict';
    } else if (errorType.toLowerCase().includes('warning')) {
      messageType = 'warning';
    }

    return (
      <ErrorMessage
        message={errorMessage}
        title="Error"
        type={messageType}
        details={data.conflict_details || data.error_details}
      />
    );
  }

  return null;
};

export default CollaborationMessage;
