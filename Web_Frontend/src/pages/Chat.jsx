import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { History, Plus, Send, Mic, MicOff, AlertCircle, Sparkles, X, MessageSquare, Compass, Terminal, HelpCircle } from 'lucide-react';
import { useChat } from '../contexts/ChatContext';
import { useAuth } from '../contexts/AuthContext';
import DemoChatBubble from '../components/DemoChatBubble';
import './Chat.css';

export const Chat = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { messages, isEvaTyping, conversations, selectedSessionId, selectConversation, sendMessage, clearChat } = useChat();
  const location = useLocation();
  const initialPrompt = location.state?.initialPrompt;

  const [inputText, setInputText] = useState('');
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  
  const scrollRef = useRef(null);
  const recognitionRef = useRef(null);

  const suggestions = [
    { title: 'Schedule study slots', prompt: 'Add FYP meeting Friday 3pm' },
    { title: 'Create roadmaps', prompt: 'Make Python roadmap for 2 weeks' },
    { title: 'Set alert notifications', prompt: 'Remind me before NLP exam' },
    { title: 'Review study metrics', prompt: 'Show my weekly progress' },
  ];

  // Speech Recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setSpeechSupported(true);
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = 'en-US';

      rec.onstart = () => {
        setIsListening(true);
      };

      rec.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInputText(prev => prev + (prev ? ' ' : '') + transcript);
      };

      rec.onerror = (e) => {
        console.error('Speech recognition error', e);
        setIsListening(false);
      };

      rec.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = rec;
    }
  }, []);

  const toggleListening = () => {
    if (!speechSupported) {
      alert('Speech-to-text is not supported in this browser. Try Chrome!');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
    }
  };

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isEvaTyping]);

  // If arriving with an initial prompt (e.g. from Roadmap "Create Roadmap"), send it
  useEffect(() => {
    if (initialPrompt) {
      // sendMessage is safe to call; it will create a session if needed
      sendMessage(initialPrompt, 'text');
      // clear the location state to avoid re-sending on navigation
      try { window.history.replaceState({}, document.title, window.location.pathname); } catch {}
    }
  }, [initialPrompt]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    
    sendMessage(inputText.trim(), isListening ? 'voice' : 'text');
    setInputText('');
    if (isListening) {
      recognitionRef.current.stop();
    }
  };

  const handleSuggestionClick = (prompt) => {
    sendMessage(prompt, 'text');
  };

  const handleSelectTimeSlot = async (slot) => {
    const promptText = `I select slot: ${slot.label || `${slot.start_time} - ${slot.end_time}`}`;
    await sendMessage(promptText, 'text');
  };

  const userInitial = user?.name ? user.name.charAt(0).toUpperCase() : 'A';

  return (
    <div className="chat-playground animate-fade-in">
      
      {/* 1. Left Sidebar: Conversations Log */}
      <div className={`chat-history-sidebar ${isHistoryOpen ? 'mobile-open' : ''}`}>
        <div className="sidebar-header-saas">
          <div className="logo-brand-mini" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
            <span className="logo-text font-logo">Eva</span>
            <span className="logo-badge">AI</span>
          </div>
          <button className="mobile-close-btn" onClick={() => setIsHistoryOpen(false)}>
            <X size={18} />
          </button>
        </div>

        <button 
          className="btn btn-primary new-chat-btn-saas"
          onClick={() => {
            clearChat();
            setIsHistoryOpen(false);
          }}
        >
          <Plus size={16} style={{ marginRight: '6px' }} /> New Conversation
        </button>

        <div className="convo-list-scroll">
          <span className="convo-list-title">Recent Conversations</span>
          {conversations.length === 0 ? (
            <div className="empty-history-indicator">
              <span>No recent chats</span>
            </div>
          ) : (
            conversations.map(convo => (
              <button
                key={convo.id}
                className={`convo-row-btn ${selectedSessionId === convo.id ? 'active' : ''}`}
                onClick={() => {
                  selectConversation(convo.id);
                  setIsHistoryOpen(false);
                }}
              >
                <MessageSquare size={14} className="convo-icon" />
                <div className="convo-row-text">
                  <span className="convo-title-label">{convo.title}</span>
                  <span className="convo-subtitle-label">{convo.lastMessage}</span>
                </div>
              </button>
            ))
          )}
        </div>

        <div className="sidebar-footer-info">
          <AlertCircle size={14} className="footer-icon" />
          <p>EVA updates tasks, settings, and roadmaps in real-time across threads.</p>
        </div>
      </div>

      {/* 2. Center Panel: Message Thread & Input */}
      <div className="chat-thread-container">
        
        {/* Thread Header */}
        <header className="chat-thread-header">
          <div className="header-left-meta">
            <div className="eva-avatar-mini">E</div>
            <div className="eva-meta-text">
              <h3>EVA Virtual Assistant</h3>
              <div className="status-label">
                <span className="status-dot"></span>
                <span>Active Core</span>
              </div>
            </div>
          </div>
          <div className="header-right-actions">
            <button className="sidebar-trigger-btn" onClick={() => setIsHistoryOpen(true)}>
              <History size={18} />
              <span>History</span>
            </button>
          </div>
        </header>

        {/* Message Panel */}
        <div className="chat-messages-viewport" ref={scrollRef}>
          {messages.length === 0 ? (
            <div className="chat-splash-view">
              <div className="splash-icon-box">
                <Sparkles size={32} />
              </div>
              <h1 className="font-logo">AI Academic Playground</h1>
              <p className="splash-subtitle">Speak or type naturally to manage schedules, plan customized study tracks, or build revision logs.</p>

              {/* Suggestions for Mobile viewports (stacked below) */}
              <div className="mobile-suggestions-grid">
                {suggestions.map((s, idx) => (
                  <button 
                    key={idx} 
                    className="mobile-suggestion-card"
                    onClick={() => handleSuggestionClick(s.prompt)}
                  >
                    <h4>{s.title}</h4>
                    <p>"{s.prompt}"</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages-list-viewport">
              {messages.map((msg, idx) => {
                const showTime = idx === 0 || (
                  new Date(msg.timestamp) - new Date(messages[idx - 1].timestamp) > 10 * 60 * 1000
                );

                return (
                  <div key={msg.id} className="message-wrapper-viewport">
                    {showTime && (
                      <div className="viewport-time-divider">
                        <span className="divider-line"></span>
                        <span className="divider-text">
                          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <span className="divider-line"></span>
                      </div>
                    )}
                    <DemoChatBubble
                      text={msg.text}
                      isEva={msg.isEva}
                      userInitial={userInitial}
                      collaborationData={msg.collaborationData}
                      onSelectTimeSlot={handleSelectTimeSlot}
                    />
                  </div>
                );
              })}
              
              {isEvaTyping && (
                <div className="chat-bubble-row-saas eva">
                  <div className="avatar-mini-eva">E</div>
                  <div className="typing-bubble-saas">
                    <span className="dot-bounce"></span>
                    <span className="dot-bounce"></span>
                    <span className="dot-bounce"></span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input sticky tray */}
        <div className="chat-input-tray-wrapper">
          <form className="chat-input-saas-form" onSubmit={handleSend}>
            <input 
              type="text" 
              className="chat-input-saas-field font-body"
              placeholder={isListening ? "Listening..." : "Ask EVA to schedule, plan roadmaps..."}
              value={inputText}
              onChange={e => setInputText(e.target.value)}
            />
            
            <div className="chat-input-actions">
              <button 
                type="button" 
                className={`tray-action-btn mic-btn ${isListening ? 'listening' : ''}`}
                onClick={toggleListening}
                title="Voice Dictation"
              >
                {isListening ? <MicOff size={18} /> : <Mic size={18} />}
              </button>
              
              <button 
                type="submit" 
                className="tray-send-btn"
                disabled={!inputText.trim()}
                title="Send Message"
              >
                <Send size={16} />
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* 3. Right Sidebar: Presets & Guides */}
      <div className="chat-guides-sidebar">
        <div className="guides-header">
          <Compass size={16} className="guide-header-icon" />
          <span>Interactive Presets</span>
        </div>
        
        <div className="guides-scroll">
          <div className="guide-section">
            <span className="guide-section-lbl">Try Asking EVA</span>
            <div className="preset-prompts-list">
              {suggestions.map((s, idx) => (
                <button 
                  key={idx} 
                  className="preset-prompt-btn"
                  onClick={() => handleSuggestionClick(s.prompt)}
                >
                  <div className="preset-top">
                    <span className="preset-title">{s.title}</span>
                    <Terminal size={12} className="preset-icon" />
                  </div>
                  <p className="preset-body">"{s.prompt}"</p>
                </button>
              ))}
            </div>
          </div>

          <div className="guide-section border-top">
            <span className="guide-section-lbl">Capabilities Guide</span>
            <div className="capability-card-info">
              <HelpCircle size={14} className="cap-icon" />
              <div>
                <h5>Chained Tasks</h5>
                <p>Use "before" or "after" clauses to schedule dependencies automatically.</p>
              </div>
            </div>
            <div className="capability-card-info">
              <HelpCircle size={14} className="cap-icon" />
              <div>
                <h5>Custom Paths</h5>
                <p>Prompt with topic + duration (e.g., "Python for 2 weeks") to build roadmaps.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
};

export default Chat;
