import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Player } from '@lottiefiles/react-lottie-player';
import { ArrowRight, Sparkles } from 'lucide-react';
import './Welcome.css';

export const Welcome = () => {
  const navigate = useNavigate();

  return (
    <div className="welcome-screen animate-fade-in">
      <div className="welcome-glow-mesh"></div>
      
      <header className="welcome-navbar">
        <div className="navbar-logo" onClick={() => navigate('/') } style={{ cursor: 'pointer' }}>
          <span className="logo-text font-logo">EVA</span>
          <span className="logo-badge">AI</span>
        </div>
        <button 
          className="nav-signin-btn" 
          onClick={() => navigate('/auth', { state: { initialIndex: 0 } })}
        >
          Sign In
        </button>
      </header>

      <main className="welcome-hero">
        <div className="hero-left">
          <div className="announcement-pill">
            <Sparkles size={14} className="sparkle-icon" />
            <span>AI Academic Assistant for Students</span>
          </div>
          <h1 className="hero-main-title font-headline">
            Your <span className="highlight">Academic</span> Assistant
          </h1>
          <p className="hero-sub-description">
            EVA understands plain English to manage your tasks, deadlines, and study plans — all through one simple conversation powered by AI trained just for students.
          </p>
          <div className="hero-actions-row">
            <button className="btn btn-primary hero-btn" onClick={() => navigate('/get-started')}>
              Get Started <ArrowRight size={18} style={{ marginLeft: '8px' }} />
            </button>
            <button className="btn btn-outlined hero-btn-secondary" onClick={() => navigate('/features')}>
              See Features
            </button>
          </div>
        </div>

        <div className="hero-right">
          <div className="hero-visual-card">
            <div className="card-glass-glow"></div>
            <Player
              autoplay
              loop
              src="/lottie/message.json"
              style={{ height: '220px', width: '220px' }}
            />
            <div className="floating-card-pill pill-top">
              <span>📅 Parsed Midterm Friday 3pm</span>
            </div>
            <div className="floating-card-pill pill-bottom">
              <span>🧠 Python Roadmap generated</span>
            </div>
          </div>
        </div>
      </main>

      <footer className="welcome-footer-bar">
        <span className="brand-label">AI-POWERED • BUILT FOR PROFESSIONAL ACADEMICS</span>
        <div className="footer-links">
          <span>v2.0 Web Platform</span>
        </div>
      </footer>
    </div>
  );
};

export default Welcome;
