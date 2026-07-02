import React, { useState, useEffect } from 'react';
import { ChevronDown, Info, Play, CheckCircle, HelpCircle, BookOpen, AlertCircle, Sparkles, X, ExternalLink, PlayCircle } from 'lucide-react';
import apiRequest from '../services/api';
import { useCalendar } from '../contexts/CalendarContext';
import './Roadmap.css';

const MOCK_ALL_ROADMAPS = [
  {
    id: '1',
    name: 'Python',
    category: 'Programming Language',
    color: '#F59E0B',
    bg: 'rgba(245, 158, 11, 0.15)',
    desc: 'Python basics, data handling, OOP, and practical scripting.',
  },
  {
    id: '2',
    name: 'JavaScript',
    category: 'Programming Language',
    color: '#3B82F6',
    bg: 'rgba(59, 130, 246, 0.15)',
    desc: 'JavaScript fundamentals, DOM, async programming, and APIs.',
  },
  {
    id: '3',
    name: 'TypeScript',
    category: 'Programming Language',
    color: '#8B5CF6',
    bg: 'rgba(139, 92, 246, 0.15)',
    desc: 'Typed JavaScript, interfaces, generics, and modern frontend use.',
  },
  {
    id: '4',
    name: 'Java',
    category: 'Programming Language',
    color: '#10B981',
    bg: 'rgba(16, 185, 129, 0.15)',
    desc: 'Java syntax, OOP, collections, streams, and backend foundations.',
  },
  {
    id: '5',
    name: 'C#',
    category: '.NET Language',
    color: '#EC4899',
    bg: 'rgba(236, 72, 153, 0.15)',
    desc: 'C# syntax, OOP, LINQ, and .NET development basics.',
  },
  {
    id: '6',
    name: 'C++',
    category: 'Programming Language',
    color: '#14B8A6',
    bg: 'rgba(20, 184, 166, 0.15)',
    desc: 'C++ fundamentals, memory, STL, OOP, and performance-focused coding.',
  },
  {
    id: '7',
    name: 'Go (Golang)',
    category: 'Programming Language',
    color: '#6366F1',
    bg: 'rgba(99, 102, 241, 0.15)',
    desc: 'Go syntax, concurrency, packages, and backend service development.',
  }
];

const MOCK_USER_ROADMAPS = [
  {
    id: '1',
    name: 'Python',
    language: 'Python',
    category: 'Programming Language',
    color: '#F59E0B',
    bg: 'rgba(245, 158, 11, 0.15)',
    progress_percent: 33,
    sessions: [
      {
        id: 'py1',
        title: 'Basics',
        description: 'Syntax, variables, conditions, loops, and functions.',
        status: 'completed',
        scheduled_date: 'Mon · 9:00 AM',
        estimated_duration: 60,
        resources: [{ title: 'Watch Intro', url: 'https://youtube.com' }],
        session_state: 'completed',
        is_current: false,
      },
      {
        id: 'py2',
        title: 'Data Structures',
        description: 'Work with lists, dictionaries, sets, and tuples.',
        status: 'ongoing',
        scheduled_date: 'Tue · 10:00 AM',
        estimated_duration: 90,
        resources: [{ title: 'Watch Guide', url: 'https://youtube.com' }],
        session_state: 'current',
        is_current: true,
      },
      {
        id: 'py3',
        title: 'Functions',
        description: 'Define and use functions, understand scope and lambdas.',
        status: 'pending',
        scheduled_date: 'Wed · 11:00 AM',
        estimated_duration: 75,
        resources: [{ title: 'Watch Advanced', url: 'https://youtube.com' }],
        session_state: 'locked',
        is_current: false,
      }
    ]
  },
  {
    id: '2',
    name: 'JavaScript',
    language: 'JavaScript',
    category: 'Programming Language',
    color: '#3B82F6',
    bg: 'rgba(59, 130, 246, 0.15)',
    progress_percent: 50,
    sessions: [
      {
        id: 'js1',
        title: 'Basics',
        description: 'Learn syntax, variables, and control flow.',
        status: 'completed',
        scheduled_date: 'Mon · 11:00 AM',
        estimated_duration: 60,
        resources: [{ title: 'Intro to JS', url: 'https://youtube.com' }],
        session_state: 'completed',
        is_current: false,
      },
      {
        id: 'js2',
        title: 'DOM',
        description: 'Manipulate elements and handle browser events.',
        status: 'ongoing',
        scheduled_date: 'Wed · 1:00 PM',
        estimated_duration: 90,
        resources: [{ title: 'DOM Manipulation', url: 'https://youtube.com' }],
        session_state: 'current',
        is_current: true,
      }
    ]
  }
];

export const Roadmap = () => {
  const [userRoadmaps, setUserRoadmaps] = useState([]);
  const [selectedRoadmapId, setSelectedRoadmapId] = useState('');
  const [activeNode, setActiveNode] = useState(null);
  const [showInfoDrawer, setShowInfoDrawer] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [scheduleDates, setScheduleDates] = useState([]);

  const { fetchDashboard } = useCalendar() || {};

  const fetchRoadmapDetails = async (goalId) => {
    if (goalId === '1' || goalId === '2') return;
    setIsLoading(true);
    try {
      const response = await apiRequest(`/api/roadmaps/${goalId}`);
      if (response.status === 'success' && response.data?.roadmap) {
        const r = response.data.roadmap;
        setUserRoadmaps(prev => prev.map(item => {
          if (item.id === goalId) {
            return {
              ...item,
              name: r.language || r.title,
              language: r.language,
              category: r.track_label || 'Study Track',
              progress_percent: r.progress_percent || 0,
              status: r.status,
              sessions: (r.sessions || []).map(s => ({
                id: s.id || s._id,
                title: s.title,
                description: s.description,
                status: s.status,
                scheduled_date: s.scheduled_date ? formatBackendDate(s.scheduled_date) : 'Flexible',
                estimated_duration: s.estimated_duration || 60,
                resources: s.resources || [],
                session_state: s.session_state || 'locked',
                is_current: s.is_current || false,
              }))
            };
          }
          return item;
        }));

        // Keep details panel in sync if open
        if (activeNode) {
          const freshNode = (r.sessions || []).find(s => (s.id || s._id) === activeNode.id);
          if (freshNode) {
            setActiveNode({
              id: freshNode.id || freshNode._id,
              title: freshNode.title,
              description: freshNode.description,
              status: freshNode.status,
              scheduled_date: freshNode.scheduled_date ? formatBackendDate(freshNode.scheduled_date) : 'Flexible',
              estimated_duration: freshNode.estimated_duration || 60,
              resources: freshNode.resources || [],
              session_state: freshNode.session_state || 'locked',
              is_current: freshNode.is_current || false,
            });
          }
        }
      }
    } catch (err) {
      console.error('Failed to load roadmap details:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchUserRoadmaps = async () => {
    setIsLoading(true);
    try {
      const response = await apiRequest('/api/roadmaps/plans');
      if (response.status === 'success' && response.data?.roadmaps && response.data.roadmaps.length > 0) {
        const mapped = response.data.roadmaps.map(r => ({
          id: r.id || r._id,
          name: r.language || r.title,
          language: r.language,
          category: r.track_label || 'Study Track',
          color: getLangColor(r.language),
          bg: getLangBgColor(r.language),
          progress_percent: r.progress_percent || 0,
          status: r.status,
          sessions: []
        }));
        setUserRoadmaps(mapped);
        
        // Pick the first roadmap plan as default if none is currently selected
        const currentSelectedId = selectedRoadmapId;
        if (!currentSelectedId || !mapped.some(m => m.id === currentSelectedId)) {
          setSelectedRoadmapId(mapped[0].id);
        } else {
          fetchRoadmapDetails(currentSelectedId);
        }
      } else {
        setUserRoadmaps(MOCK_USER_ROADMAPS);
        setSelectedRoadmapId(MOCK_USER_ROADMAPS[0].id);
      }
    } catch (err) {
      console.warn('Could not load real roadmaps plans, loading fallback data.', err);
      setUserRoadmaps(MOCK_USER_ROADMAPS);
      setSelectedRoadmapId(MOCK_USER_ROADMAPS[0].id);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchScheduleDates = async (goalId) => {
    if (goalId === '1' || goalId === '2') return;
    try {
      const response = await apiRequest(`/api/roadmaps/${goalId}/schedule-dates`);
      if (response.status === 'success' && response.data?.dates) {
        setScheduleDates(response.data.dates);
      } else {
        setScheduleDates([]);
      }
    } catch (err) {
      console.error('Failed to fetch schedule dates:', err);
      setScheduleDates([]);
    }
  };

  useEffect(() => {
    fetchUserRoadmaps();
  }, []);

  useEffect(() => {
    if (selectedRoadmapId) {
      fetchRoadmapDetails(selectedRoadmapId);
    }
  }, [selectedRoadmapId]);

  useEffect(() => {
    if (activeNode && activeNode.is_current && selectedRoadmapId && selectedRoadmapId !== '1' && selectedRoadmapId !== '2') {
      fetchScheduleDates(selectedRoadmapId);
    } else {
      setScheduleDates([]);
    }
  }, [activeNode, selectedRoadmapId]);

  const handleUpdateSessionStatus = async (status) => {
    if (!selectedRoadmapId || !activeNode) return;
    setIsLoading(true);
    try {
      await apiRequest(`/api/learning/${selectedRoadmapId}/sessions/${activeNode.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status })
      });
      alert(`Topic marked as ${status}!`);
      if (fetchDashboard) fetchDashboard();
      await fetchRoadmapDetails(selectedRoadmapId);
    } catch (err) {
      alert(err.message || `Failed to mark topic as ${status}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRescheduleSession = async (dateStr) => {
    if (!selectedRoadmapId || !activeNode || !dateStr) return;
    setIsLoading(true);
    try {
      await apiRequest(`/api/learning/${selectedRoadmapId}/sessions/${activeNode.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ scheduled_date: dateStr })
      });
      alert('Topic rescheduled successfully!');
      if (fetchDashboard) fetchDashboard();
      await fetchRoadmapDetails(selectedRoadmapId);
    } catch (err) {
      alert(err.message || 'Failed to reschedule topic');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateGoalStatus = async (newStatus) => {
    if (!selectedRoadmapId) return;
    if (newStatus === 'cancelled' && !window.confirm('Are you sure you want to cancel this learning plan? This will delete all mapped tasks.')) {
      return;
    }
    setIsLoading(true);
    try {
      await apiRequest(`/api/learning/${selectedRoadmapId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus })
      });
      alert(`Learning plan marked as ${newStatus}!`);
      if (fetchDashboard) fetchDashboard();
      await fetchUserRoadmaps();
    } catch (err) {
      alert(err.message || 'Failed to update plan status');
    } finally {
      setIsLoading(false);
    }
  };

  const getLangColor = (lang) => {
    const found = MOCK_ALL_ROADMAPS.find(l => l.name.toLowerCase() === (lang || '').toLowerCase());
    return found ? found.color : '#F59E0B';
  };

  const getLangBgColor = (lang) => {
    const found = MOCK_ALL_ROADMAPS.find(l => l.name.toLowerCase() === (lang || '').toLowerCase());
    return found ? found.bg : 'rgba(245, 158, 11, 0.15)';
  };

  const formatBackendDate = (dateStr) => {
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const hours = d.getHours();
      const minutes = d.getMinutes();
      const ampm = hours >= 12 ? 'PM' : 'AM';
      const formattedHours = hours % 12 || 12;
      const formattedMins = minutes.toString().padStart(2, '0');
      return `${days[d.getDay()]} · ${formattedHours}:${formattedMins} ${ampm}`;
    } catch {
      return dateStr;
    }
  };

  const currentRoadmap = userRoadmaps.find(r => r.id === selectedRoadmapId) || userRoadmaps[0];

  const handleNodeClick = (node) => {
    setActiveNode(node);
  };

  return (
    <div className="roadmap-workspace animate-fade-in">
      
      {/* 1. Left Sidebar: Roadmap Stats & Available Directory */}
      <div className="roadmap-left-pane">
        <div className="pane-header-container">
          <BookOpen size={20} className="pane-icon" />
          <h3 className="pane-title font-logo">Roadmaps</h3>
        </div>

        {/* Current Roadmap Overview Card */}
        {currentRoadmap && (
          <div className="current-roadmap-overview-card" style={{ '--accent-color': currentRoadmap.color }}>
            <span className="overview-lbl">Active Track</span>
            <div className="custom-dropdown-container-saas">
              <select
                value={selectedRoadmapId}
                onChange={(e) => setSelectedRoadmapId(e.target.value)}
                className="roadmap-select-saas font-body"
              >
                {userRoadmaps.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
              <ChevronDown size={16} className="dropdown-arrow-saas" />
            </div>

            <div className="overview-stats">
              <div className="stat-row">
                <span>Progress</span>
                <strong>{currentRoadmap.progress_percent}%</strong>
              </div>
              <div className="progress-bar-container-saas">
                <div 
                  className="progress-bar-fill-saas" 
                  style={{ width: `${currentRoadmap.progress_percent}%`, backgroundColor: currentRoadmap.color }}
                />
              </div>
              {currentRoadmap.status && (
                <>
                  <div className="stat-row" style={{ marginTop: 12, marginBottom: 4 }}>
                    <span>Status</span>
                    <span className={`status-badge-saas ${currentRoadmap.status}`}>
                      {currentRoadmap.status}
                    </span>
                  </div>
                </>
              )}
            </div>

            {selectedRoadmapId !== '1' && selectedRoadmapId !== '2' && currentRoadmap.status && (
              <div className="goal-actions-row">
                {currentRoadmap.status === 'active' && (
                  <button className="goal-action-btn pause-btn" onClick={() => handleUpdateGoalStatus('paused')}>
                    Pause Plan
                  </button>
                )}
                {currentRoadmap.status === 'paused' && (
                  <button className="goal-action-btn resume-btn" onClick={() => handleUpdateGoalStatus('active')}>
                    Resume Plan
                  </button>
                )}
                {currentRoadmap.status !== 'cancelled' && currentRoadmap.status !== 'completed' && (
                  <button className="goal-action-btn cancel-btn" onClick={() => handleUpdateGoalStatus('cancelled')}>
                    Cancel
                  </button>
                )}
              </div>
            )}
            
            <button className="directory-trigger-mobile-btn" onClick={() => setShowInfoDrawer(true)}>
              <Info size={14} /> Browse Catalog
            </button>
          </div>
        )}

        {/* Catalog List (Visible on desktop sidebar by default) */}
        <div className="desktop-catalog-panel">
          <span className="catalog-panel-title">Roadmaps Directory</span>
          <div className="catalog-scroll-list">
            {MOCK_ALL_ROADMAPS.map((item) => (
              <div key={item.id} className="catalog-card-tile">
                <div className="catalog-tile-top">
                  <div className="catalog-icon-box" style={{ backgroundColor: item.bg, color: item.color }}>
                    <span>{item.name.charAt(0)}</span>
                  </div>
                  <div className="catalog-meta">
                    <h4>{item.name}</h4>
                    <span className="category-lbl">{item.category}</span>
                  </div>
                </div>
                <p className="catalog-desc">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 2. Center Panel: Interactive Alternating Trail */}
      <div className="roadmap-center-pane">
        <header className="roadmap-trail-header">
          <h2 className="trail-main-title font-logo">
            {currentRoadmap ? currentRoadmap.name : 'Learning'} Path
          </h2>
          <div className="trail-tagline">
            <Sparkles size={14} className="sparkle" />
            <span>Click any node to view learning guides & resources</span>
          </div>
        </header>

        <div className="roadmap-trail-viewport">
          {currentRoadmap && currentRoadmap.sessions && currentRoadmap.sessions.length > 0 ? (
            <div className="trail-winding-scaffold">
              <div className="winding-nodes-list">
                {currentRoadmap.sessions.map((node, index) => {
                  const isEven = index % 2 === 0;
                  const isCompleted = node.status === 'completed' || node.status === 'complete';
                  const isOngoing = node.status === 'ongoing' || node.status === 'active';
                  const color = currentRoadmap.color;

                  return (
                    <div 
                      key={node.id} 
                      className={`trail-node-row ${isEven ? 'left-align' : 'right-align'}`}
                    >
                      <button 
                        className={`trail-node-card ${isCompleted ? 'completed' : ''} ${isOngoing ? 'active' : ''} ${activeNode?.id === node.id ? 'focused' : ''}`}
                        onClick={() => handleNodeClick(node)}
                        style={{ borderLeft: `4px solid ${color}` }}
                      >
                        <div className="node-avatar-indicator">
                          <div className="indicator-pulse" style={{ backgroundColor: isOngoing ? color : 'transparent' }}></div>
                          <div className="indicator-core" style={{ backgroundColor: isCompleted ? '#22c55e' : (isOngoing ? color : 'var(--color-border)') }}>
                            {isCompleted ? (
                              <CheckCircle size={16} color="white" />
                            ) : (
                              <Play size={14} color={isOngoing ? 'white' : 'var(--color-text-secondary)'} style={{ marginLeft: isOngoing ? '1px' : '0' }} />
                            )}
                          </div>
                        </div>

                        <div className="node-card-body">
                          <h4 className="node-title">{node.title}</h4>
                          <p className="node-desc-trimmed">{node.description || 'Topic Overview'}</p>
                          <div className="node-badges-row">
                            <span className="badge duration">{node.estimated_duration} min</span>
                            <span className="badge date">{node.scheduled_date}</span>
                          </div>
                        </div>
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="empty-roadmap-state">
              <AlertCircle size={44} className="empty-icon" />
              <h4>No roadmap generated</h4>
              <p>Ask EVA to generate a study roadmap for you in the AI Chat.</p>
              <button className="goto-chat-btn" onClick={() => navigate('/chat')}>
                Create Roadmap
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 3. Right Panel Sidebar: Node Details Drawer */}
      <div className={`roadmap-right-pane ${activeNode ? 'open' : ''}`}>
        {activeNode ? (
          <div className="node-details-wrapper">
            <header className="details-header">
              <span className="details-eyebrow">Topic Details</span>
              <button className="details-close-btn" onClick={() => setActiveNode(null)}>
                <X size={18} />
              </button>
            </header>

            <div className="details-body">
              <h3 className="details-title font-logo">{activeNode.title}</h3>
              <p className="details-desc">{activeNode.description || 'No detailed overview provided. Click watch guide to learn more about this session.'}</p>
              
              <div className="details-meta-box">
                <div className="meta-tile">
                  <span>Duration</span>
                  <strong>{activeNode.estimated_duration} mins</strong>
                </div>
                <div className="meta-tile">
                  <span>Scheduled Date</span>
                  <strong>{activeNode.scheduled_date}</strong>
                </div>
              </div>

              {activeNode.is_current && selectedRoadmapId !== '1' && selectedRoadmapId !== '2' && (
                <div className="node-actions-container">
                  <span className="resource-section-lbl">Session Actions</span>
                  <div className="action-buttons-row">
                    {(activeNode.session_state === 'ongoing' || activeNode.session_state === 'overdue' || activeNode.status === 'ongoing') && (
                      <button 
                        className="action-btn complete-btn"
                        onClick={() => handleUpdateSessionStatus('completed')}
                      >
                        <CheckCircle size={14} /> Complete Topic
                      </button>
                    )}
                    {(activeNode.session_state === 'unlocked_future' || activeNode.session_state === 'upcoming') && (
                      <button 
                        className="action-btn skip-btn"
                        onClick={() => handleUpdateSessionStatus('skipped')}
                      >
                        <Play size={14} /> Skip Topic
                      </button>
                    )}
                  </div>
                  
                  {/* Reschedule Dropdown */}
                  {scheduleDates.length > 0 && (
                    <div className="reschedule-dropdown-container">
                      <label className="reschedule-lbl">Reschedule Topic</label>
                      <div className="custom-dropdown-container-saas">
                        <select
                          className="roadmap-select-saas font-body"
                          defaultValue=""
                          onChange={(e) => {
                            if (e.target.value) {
                              handleRescheduleSession(e.target.value);
                            }
                          }}
                        >
                          <option value="" disabled>Select new study slot...</option>
                          {scheduleDates.map((item, idx) => (
                            <option key={idx} value={item.date}>
                              {item.day_label} · {item.date} ({item.time})
                            </option>
                          ))}
                        </select>
                        <ChevronDown size={14} className="dropdown-arrow-saas" />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeNode.resources && activeNode.resources.length > 0 ? (
                <div className="details-resources">
                  <span className="resource-section-lbl">YouTube Video Tutorial</span>
                  {activeNode.resources.map((res, rIdx) => (
                    <a 
                      key={rIdx} 
                      href={res.url || 'https://youtube.com'} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="youtube-resource-btn"
                    >
                      <PlayCircle size={18} className="yt-icon" />
                      <div className="btn-text">
                        <span>{res.title || 'Watch Tutorial'}</span>
                        <p>Open YouTube in a new tab</p>
                      </div>
                      <ExternalLink size={14} className="launch-icon" />
                    </a>
                  ))}
                </div>
              ) : (
                <div className="details-resources-empty">
                  <HelpCircle size={18} />
                  <span>No video resources attached to this topic.</span>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="right-pane-placeholder">
            <Info size={24} />
            <p>Select any learning topic node to view tutorial videos, schedule times, and reference descriptions.</p>
          </div>
        )}
      </div>

      {/* Available Roadmaps Directory Drawer (Mobile Only) */}
      {showInfoDrawer && (
        <div className="info-drawer-backdrop-saas" onClick={() => setShowInfoDrawer(false)}>
          <div className="info-drawer-content-saas" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-handle-saas" />
            
            <div className="drawer-header-saas">
              <h3 className="drawer-title-saas font-logo">Roadmaps Directory</h3>
              <button className="close-drawer-btn-saas" onClick={() => setShowInfoDrawer(false)}>
                <X size={20} />
              </button>
            </div>

            <div className="drawer-list-saas">
              {MOCK_ALL_ROADMAPS.map((item) => (
                <div key={item.id} className="drawer-tile-saas">
                  <div className="tile-top-saas">
                    <div className="tile-icon-saas" style={{ backgroundColor: item.bg, color: item.color }}>
                      <span>{item.name.charAt(0)}</span>
                    </div>
                    <div className="tile-meta-saas">
                      <h4>{item.name}</h4>
                      <span>{item.category}</span>
                    </div>
                  </div>
                  <p className="tile-desc-saas">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default Roadmap;
