import React from 'react';
import './DemoChatBubble.css';

export const DemoChatBubble = ({ text, isEva, boldPart, userInitial = 'A' }) => {
  const renderText = () => {
    if (!boldPart) return text;
    
    const parts = text.split(boldPart);
    return (
      <>
        {parts[0]}
        <strong>{boldPart}</strong>
        {parts[1]}
      </>
    );
  };

  return (
    <div className={`chat-bubble-row ${isEva ? 'eva' : 'user'}`}>
      {isEva && (
        <div className="avatar avatar-eva font-body">
          <span>E</span>
        </div>
      )}
      
      <div className="bubble-content">
        <p className="bubble-text">{renderText()}</p>
      </div>

      {!isEva && (
        <div className="avatar avatar-user font-body">
          <span>{userInitial}</span>
        </div>
      )}
    </div>
  );
};

export default DemoChatBubble;
