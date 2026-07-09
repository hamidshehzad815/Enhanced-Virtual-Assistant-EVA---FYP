import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import DemoChatBubble from '../components/DemoChatBubble';
import { Sparkles, ArrowRight, UserPlus, LogIn } from 'lucide-react';
import './GetStarted.css';

export const GetStarted = () => {
  const navigate = useNavigate();
  
  const fullText = 'Meet Your Personal Digital Secretary';
  const [displayedText, setDisplayedText] = useState('');
  const [charIndex, setCharIndex] = useState(0);
  const [visibleBubbles, setVisibleBubbles] = useState([false, false, false, false, false]);
  const [buttonsVisible, setButtonsVisible] = useState(false);

  const messages = [
    { text: 'Hey Areej! What do you need today? 😊', isEva: true },
    { text: 'Add NLP Mid exam at Monday 5pm high priority', isEva: false },
    {
      text: 'Done! "NLP Mid exam" added for Monday at 5pm. Anything else?',
      isEva: true,
      boldPart: 'NLP Mid exam',
    },
    { text: 'Make Python Roadmap for 2 weeks', isEva: false },
    {
      text: "Learning plan ready — 5 topics, all scheduled. Let's go!",
      isEva: true,
    },
  ];

  // Typewriter effect
  useEffect(() => {
    let timer;
    if (charIndex < fullText.length) {
      timer = setTimeout(() => {
        setDisplayedText(fullText.substring(0, charIndex + 1));
        setCharIndex(prev => prev + 1);
      }, 35);
    } else {
      startBubblesSequence();
    }
    return () => clearTimeout(timer);
  }, [charIndex]);

  const startBubblesSequence = async () => {
    for (let i = 0; i < messages.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 450));
      setVisibleBubbles(prev => {
        const next = [...prev];
        next[i] = true;
        return next;
      });
    }
    await new Promise(resolve => setTimeout(resolve, 500));
    setButtonsVisible(true);
  };

  const renderTypewriterText = () => {
    const textPart1 = displayedText.replace('Digital Secretary', '');
    const hasSec = displayedText.includes('Digital Secretary');
    
    return (
      <h1 className="typewriter-headline font-body">
        {textPart1}
        {hasSec && <span className="highlight font-headline">Digital Secretary</span>}
        {charIndex < fullText.length && <span className="cursor">|</span>}
      </h1>
    );
  };

  return (
    <div className="getstarted-screen animate-fade-in">
      <div className="getstarted-glow-mesh"></div>

      <header className="getstarted-navbar">
        <div className="navbar-logo" onClick={() => navigate('/welcome')}>
          <span className="logo-text font-logo">EVA</span>
          <span className="logo-badge">PREVIEW</span>
        </div>
      </header>

      <main className="getstarted-main">
        <div className="getstarted-left">
          <div className="preview-badge">
            <Sparkles size={14} className="sparkle-icon" />
            <span>Interactive Assistant Preview</span>
          </div>
          
          <div className="headline-section">
            {renderTypewriterText()}
            <p className="sub-label font-body">
              An intelligent, conversational virtual assistant designed to manage task lifecycles, generate custom study paths, and sync priority events automatically.
            </p>
          </div>

          <div className={`buttons-panel ${buttonsVisible ? 'visible' : ''}`}>
            <button 
              className="btn btn-primary btn-signup"
              onClick={() => navigate('/auth', { state: { initialIndex: 1 } })}
            >
              Create Free Account <UserPlus size={18} style={{ marginLeft: '8px' }} />
            </button>
            
            <button 
              className="btn-signin"
              onClick={() => navigate('/auth', { state: { initialIndex: 0 } })}
            >
              Already have an account? <span className="link-text">Sign In <LogIn size={14} style={{ display: 'inline', marginLeft: '4px' }} /></span>
            </button>
          </div>
        </div>

        <div className="getstarted-right">
          {/* Demo Chat Card */}
          <div className="demo-chat-card">
            <div className="chat-card-header">
              <div className="eva-avatar-circle">E</div>
              <div className="chat-card-header-text">
                <h4>EVA</h4>
                <div className="status-indicator">
                  <span className="status-pulse"></span>
                  <p className="online-indicator">Online — ready to help</p>
                </div>
              </div>
            </div>

            <div className="chat-card-body">
              {messages.map((msg, idx) => (
                <div 
                  key={idx} 
                  className={`bubble-anim-wrapper ${visibleBubbles[idx] ? 'visible' : ''}`}
                >
                  <DemoChatBubble
                    text={msg.text}
                    isEva={msg.isEva}
                    boldPart={msg.boldPart}
                    userInitial="A"
                  />
                </div>
              ))}
            </div>
            
            <div className="chat-card-input-placeholder">
              <span>Ask EVA anything...</span>
              <button className="chat-send-btn-placeholder">Send</button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default GetStarted;
