import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Home, Calendar, MessageSquare, Route, BarChart2, MoreHorizontal, Users, Settings, LogOut, X, ChevronRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import './AppShell.css';

export const AppShell = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout, user } = useAuth();
  
  const [isMoreOpen, setIsMoreOpen] = useState(false);

  // Tabs for mobile nav (includes "More" tab)
  const mobileTabs = [
    { label: 'Home', path: '/', icon: Home },
    { label: 'Calendar', path: '/calendar', icon: Calendar },
    { label: 'Chat', path: '/chat', icon: MessageSquare },
    { label: 'Roadmap', path: '/roadmap', icon: Route },
    { label: 'Analytics', path: '/analytics', icon: BarChart2 },
    { label: 'More', path: '__more__', icon: MoreHorizontal }
  ];

  // Sidebar items for desktop nav (directly shows Collaboration and Settings)
  const desktopMenuItems = [
    { label: 'Dashboard', path: '/', icon: Home },
    { label: 'Study Calendar', path: '/calendar', icon: Calendar },
    { label: 'AI Assistant Chat', path: '/chat', icon: MessageSquare },
    { label: 'Learning Roadmaps', path: '/roadmap', icon: Route },
    { label: 'Productivity Analytics', path: '/analytics', icon: BarChart2 },
    { label: 'Buddies & Social', path: '/collaboration', icon: Users },
    { label: 'Settings', path: '/settings', icon: Settings }
  ];

  const activeMobileIndex = () => {
    const path = location.pathname;
    if (path === '/') return 0;
    if (path.startsWith('/calendar')) return 1;
    if (path.startsWith('/chat')) return 2;
    if (path.startsWith('/roadmap')) return 3;
    if (path.startsWith('/analytics')) return 4;
    if (path.startsWith('/settings') || path.startsWith('/collaboration')) return 5;
    return 0;
  };

  return (
    <div className="app-container">
      {/* Desktop Sidebar Navigation */}
      <aside className="desktop-sidebar">
        <div className="sidebar-brand">
          <span className="auth-logo font-logo" style={{ marginBottom: 0, fontSize: '28px' }}>Eva</span>
          <span className="brand-badge">WEB</span>
        </div>

        {user && (
          <div className="sidebar-profile">
            <div className="profile-avatar">
              {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="profile-details">
              <span className="profile-name">{user.name || 'User'}</span>
              <span className="profile-email">@{user.username || 'username'}</span>
            </div>
          </div>
        )}

        <nav className="sidebar-menu">
          {desktopMenuItems.map((item, idx) => {
            const IconComponent = item.icon;
            const isActive = location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path));
            return (
              <button
                key={idx}
                className={`sidebar-menu-item ${isActive ? 'active' : ''}`}
                onClick={() => navigate(item.path)}
              >
                <IconComponent size={20} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <button 
            className="sidebar-menu-item logout-btn" 
            onClick={() => {
              logout();
              navigate('/welcome');
            }}
          >
            <LogOut size={20} />
            <span>Log Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="main-content">
        <div className="scrollable-content">
          {children}
        </div>
      </div>

      {/* Mobile Bottom Navigation */}
      <nav className="mobile-navbar">
        <div className="mobile-nav-items">
          {mobileTabs.map((tab, idx) => {
            const IconComponent = tab.icon;
            const isActive = idx === activeMobileIndex();
            return (
              <button
                key={idx}
                className={`mobile-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => {
                  if (tab.path === '__more__') {
                    setIsMoreOpen(true);
                  } else {
                    navigate(tab.path);
                  }
                }}
              >
                <div className="icon-wrapper">
                  <IconComponent size={22} />
                </div>
                <span className="nav-label">{tab.label}</span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* More Options Bottom Sheet */}
      {isMoreOpen && (
        <div className="bottom-sheet-overlay" onClick={() => setIsMoreOpen(false)}>
          <div className="bottom-sheet-content" onClick={e => e.stopPropagation()}>
            <div className="bottom-sheet-handle"></div>
            
            <div className="sheet-header">
              <h3>More Options</h3>
              <button className="close-btn" onClick={() => setIsMoreOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="sheet-list">
              <button 
                className="sheet-item" 
                onClick={() => {
                  setIsMoreOpen(false);
                  navigate('/collaboration');
                }}
              >
                <div className="sheet-icon-box friends">
                  <Users size={22} />
                </div>
                <div className="sheet-item-text">
                  <h4>Friends & Collaborators</h4>
                  <p>Study together, share tasks</p>
                </div>
                <ChevronRight className="chevron" size={18} />
              </button>

              <button 
                className="sheet-item" 
                onClick={() => {
                  setIsMoreOpen(false);
                  navigate('/settings');
                }}
              >
                <div className="sheet-icon-box settings">
                  <Settings size={22} />
                </div>
                <div className="sheet-item-text">
                  <h4>Settings</h4>
                  <p>App preferences & account</p>
                </div>
                <ChevronRight className="chevron" size={18} />
              </button>

              <button 
                className="sheet-item logout" 
                onClick={() => {
                  setIsMoreOpen(false);
                  logout();
                  navigate('/welcome');
                }}
              >
                <div className="sheet-icon-box logout">
                  <LogOut size={22} />
                </div>
                <div className="sheet-item-text">
                  <h4>Log Out</h4>
                  <p>Sign out of your account</p>
                </div>
                <ChevronRight className="chevron" size={18} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AppShell;
