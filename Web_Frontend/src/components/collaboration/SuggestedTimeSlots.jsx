import React, { useState } from 'react';
import { Clock, ChevronRight } from 'lucide-react';
import './SuggestedTimeSlots.css';

/**
 * SuggestedTimeSlots
 * Displays suggested alternative time slots for scheduling conflicts
 * Allows user to select one and send it as a new message
 */
export const SuggestedTimeSlots = ({ 
  slots = [], 
  onSelectSlot = null,
  taskTitle = null,
  isLoading = false
}) => {
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [confirmingSelection, setConfirmingSelection] = useState(false);

  if (!slots || slots.length === 0) {
    return null;
  }

  const handleSelectSlot = (slot) => {
    setSelectedSlot(slot);
    setConfirmingSelection(true);
  };

  const handleConfirm = () => {
    if (selectedSlot && onSelectSlot) {
      onSelectSlot(selectedSlot);
      setSelectedSlot(null);
      setConfirmingSelection(false);
    }
  };

  const handleCancel = () => {
    setSelectedSlot(null);
    setConfirmingSelection(false);
  };

  const formatTime = (timeString) => {
    try {
      const date = new Date(timeString);
      return date.toLocaleString([], { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true
      });
    } catch {
      return timeString;
    }
  };

  return (
    <div className="suggested-time-slots-container">
      <div className="slots-header">
        <Clock size={16} className="slots-icon" />
        <h4>Suggested Alternative Times</h4>
      </div>

      <div className="slots-list">
        {slots.map((slot, idx) => {
          const isSelected = selectedSlot && JSON.stringify(selectedSlot) === JSON.stringify(slot);
          const startTime = slot.start_time || slot.start || slot.time;
          const endTime = slot.end_time || slot.end;
          const displayLabel = slot.label || slot.display || formatTime(startTime);
          const reason = slot.reason || null;

          return (
            <div 
              key={idx}
              className={`time-slot-card ${isSelected ? 'selected' : ''}`}
              onClick={() => handleSelectSlot(slot)}
            >
              <div className="slot-main">
                <div className="slot-time">
                  <span className="time-display">{displayLabel}</span>
                  {endTime && (
                    <span className="time-end"> - {formatTime(endTime)}</span>
                  )}
                </div>
                {reason && <p className="slot-reason">{reason}</p>}
              </div>
              <ChevronRight size={18} className="slot-chevron" />
            </div>
          );
        })}
      </div>

      {confirmingSelection && selectedSlot && (
        <div className="slot-confirmation">
          <p className="confirmation-text">
            Schedule {taskTitle ? `"${taskTitle}"` : 'task'} for <strong>{formatTime(selectedSlot.start_time || selectedSlot.start)}</strong>?
          </p>
          <div className="confirmation-buttons">
            <button 
              className="btn-confirm-yes"
              onClick={handleConfirm}
              disabled={isLoading}
            >
              {isLoading ? 'Scheduling...' : 'Confirm'}
            </button>
            <button 
              className="btn-confirm-cancel"
              onClick={handleCancel}
              disabled={isLoading}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SuggestedTimeSlots;
