import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Calendar, Award, BarChart2, Bell, Cpu, Users, ArrowRight } from 'lucide-react';
import './Features.css';

export const Features = () => {
  const navigate = useNavigate();

  const features = [
    {
      icon: Calendar,
      title: "Smart Schedule",
      description: "EVA priority calendar — type or speak \"add FYP meeting Friday 3pm\" and she schedules it instantly.",
      color: "#F59E0B",
      sizeClass: "large"
    },
    {
      icon: Award,
      title: "Learning Roadmaps",
      description: "Tell EVA what you want to learn. She designs a study plan and schedules topics for you.",
      color: "#3B82F6",
      sizeClass: "medium"
    },
    {
      icon: BarChart2,
      title: "Behavior Learning",
      description: "EVA tracks when you focus best and suggests optimal study slots based on your active habits.",
      color: "#10B981",
      sizeClass: "small"
    },
    {
      icon: Bell,
      title: "Auto Reminders",
      description: "Smart 30-minute alerts, overdue task warnings, and daily digests running silently in the background.",
      color: "#EC4899",
      sizeClass: "small"
    },
    {
      icon: Cpu,
      title: "Chained Commands",
      description: "\"Add exam revision before midterm\" — EVA understands your dependencies and constructs your schedules.",
      color: "#8B5CF6",
      sizeClass: "medium"
    },
    {
      icon: Users,
      title: "Buddy Collaboration",
      description: "Form study groups, share task lists, and tackle deadlines collaboratively inside single workspaces.",
      color: "#14B8A6",
      sizeClass: "large"
    },
  ];

  return (
    <div className="features-screen animate-fade-in">
      <div className="features-glow-mesh"></div>
      
      <header className="features-navbar">
        <div className="navbar-logo" onClick={() => navigate('/welcome')}>
          <span className="logo-text font-logo">EVA</span>
          <span className="logo-badge">FEATURES</span>
        </div>
        <button className="skip-btn" onClick={() => navigate('/get-started')}>
          Skip to Start
        </button>
      </header>

      <main className="features-main-content">
        <div className="features-header-text">
          <div className="feature-badge">
            <Sparkles size={14} />
            <span>Core Capabilities</span>
          </div>
          <h1 className="features-title">
            Everything you need, <span className="highlight font-headline">understood naturally.</span>
          </h1>
          <p className="features-subtitle">
            EVA combines high-fidelity AI semantic processing with advanced calendar planning tools to streamline your academic lifecycle.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="bento-grid">
          {features.map((feature, idx) => {
            const IconComponent = feature.icon;
            return (
              <div 
                key={idx} 
                className={`bento-card ${feature.sizeClass}`}
                style={{ '--accent-color': feature.color }}
              >
                <div className="card-top">
                  <div className="icon-wrapper" style={{ backgroundColor: `${feature.color}15`, color: feature.color }}>
                    <IconComponent size={24} />
                  </div>
                  <span className="card-index">0{idx + 1}</span>
                </div>
                <h3 className="card-title font-logo">{feature.title}</h3>
                <p className="card-description">{feature.description}</p>
                <div className="card-glow-overlay"></div>
              </div>
            );
          })}
        </div>

        <div className="features-action-footer">
          <button className="btn btn-primary start-onboarding-btn" onClick={() => navigate('/get-started')}>
            Get Started Now <ArrowRight size={18} style={{ marginLeft: '8px' }} />
          </button>
        </div>
      </main>
    </div>
  );
};

export default Features;
