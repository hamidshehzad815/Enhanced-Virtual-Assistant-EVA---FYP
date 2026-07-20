import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, Info, Play, CheckCircle, HelpCircle, BookOpen, AlertCircle, Sparkles, X, ExternalLink, PlayCircle, Lock } from 'lucide-react';
import apiRequest from '../services/api';
import { useCalendar } from '../contexts/CalendarContext';
import './Roadmap.css';

const MOCK_FIRST_PYTHON_SESSION_DATE = new Date(Date.now() + 10 * 60 * 60 * 1000).toISOString();
const MOCK_FIRST_PYTHON_SESSION_TIMESTAMP = new Date(MOCK_FIRST_PYTHON_SESSION_DATE).getTime();

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

const MOCK_USER_ROADMAPS = [];

export const Roadmap = () => {
  const navigate = useNavigate();
  const [userRoadmaps, setUserRoadmaps] = useState([]);
  const [selectedRoadmapId, setSelectedRoadmapId] = useState('');
  const [activeNode, setActiveNode] = useState(null);
  const [showInfoDrawer, setShowInfoDrawer] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [scheduleDates, setScheduleDates] = useState([]);
  const [now, setNow] = useState(new Date());
  const [showRescheduleDropdown, setShowRescheduleDropdown] = useState(false);

  const { fetchDashboard, fetchTasks } = useCalendar() || {};

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
              start_date: r.start_date || r.startDate || null,
              end_date: r.end_date || r.endDate || null,
              collaborators: r.collaborators || [],
              sessions: (r.sessions || []).map(s => ({
                id: s.id || s._id,
                title: s.title,
                description: s.description,
                status: s.status,
                scheduled_date_raw: s.scheduled_date,
                scheduled_timestamp: s.scheduled_date ? new Date(s.scheduled_date).getTime() : null,
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
              scheduled_date_raw: freshNode.scheduled_date,
              scheduled_timestamp: freshNode.scheduled_date ? new Date(freshNode.scheduled_date).getTime() : null,
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
          start_date: r.start_date || r.startDate || null,
          end_date: r.end_date || r.endDate || null,
          collaborators: r.collaborators || [],
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
        setSelectedRoadmapId(MOCK_USER_ROADMAPS[0]?.id || '');
      }
    } catch (err) {
      console.warn('Could not load real roadmaps plans, loading fallback data.', err);
      setUserRoadmaps(MOCK_USER_ROADMAPS);
      setSelectedRoadmapId(MOCK_USER_ROADMAPS[0]?.id || '');
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
    const isAvailableToReschedule = activeNode && (
      getSessionActionState(activeNode) === 'near' || 
      getSessionActionState(activeNode) === 'active'
    );
    if (isAvailableToReschedule && selectedRoadmapId && selectedRoadmapId !== '1' && selectedRoadmapId !== '2') {
      fetchScheduleDates(selectedRoadmapId);
    } else {
      setScheduleDates([]);
    }
  }, [activeNode, selectedRoadmapId]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(new Date());
    }, 60000);

    return () => window.clearInterval(timer);
  }, []);

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
      if (fetchTasks) fetchTasks();
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
      if (fetchTasks) fetchTasks();
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

  const formatRoadmapDate = (value) => {
    if (!value) return '—';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const getSessionActionState = (node) => {
    const normalizedStatus = (node?.status || '').toLowerCase();
    const normalizedNodeState = (node?.session_state || '').toLowerCase();
    const isCompleted = normalizedStatus === 'completed' || normalizedStatus === 'complete' || normalizedNodeState === 'completed';
    if (isCompleted) return 'completed';

    const isSkipped = normalizedStatus === 'skipped' || normalizedNodeState === 'skipped';
    if (isSkipped) return 'skipped';

    const scheduledTimestamp = node?.scheduled_timestamp ||
      (node?.scheduled_date_raw ? new Date(node.scheduled_date_raw).getTime() : null) ||
      (node?.scheduled_date ? new Date(node.scheduled_date).getTime() : null);
    if (!scheduledTimestamp || Number.isNaN(scheduledTimestamp)) return 'upcoming';

    const diffMs = scheduledTimestamp - now.getTime();
    const oneDayMs = 24 * 60 * 60 * 1000;

    if (diffMs > oneDayMs) return 'locked';
    if (diffMs <= 0) return 'active';
    return 'near';
  };

  const handleNodeClick = (node) => {
    setActiveNode(node);
    setShowRescheduleDropdown(false);
  };

  const handleQuickReschedule = () => {
    if (scheduleDates.length > 0 && scheduleDates[0]?.date) {
      handleRescheduleSession(scheduleDates[0].date);
      return;
    }

    alert('No reschedule slots are available right now.');
  };

  return (
    <div className="roadmap-workspace animate-fade-in">
      
      {/* 1. Left Sidebar: Roadmap Stats & Available Directory */}
      <div className="roadmap-left-pane">
        <div className="pane-header-container">
          <BookOpen size={20} className="pane-icon" />
          <h3 className="pane-title font-logo">Roadmaps</h3>
        </div>

        <div className="active-tracks-section">
          <span className="catalog-panel-title">Active Tracks</span>
          <div className="active-tracks-list">
            {userRoadmaps.map((roadmap) => {
              const totalSessions = roadmap.sessions?.length || 0;
              const completedSessions = roadmap.sessions?.filter((session) => {
                const normalizedStatus = (session?.status || '').toLowerCase();
                return normalizedStatus === 'completed' || normalizedStatus === 'complete';
              }).length || 0;
              const isSelected = selectedRoadmapId === roadmap.id;

              return (
                <button
                  key={roadmap.id}
                  type="button"
                  className={`active-track-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => setSelectedRoadmapId(roadmap.id)}
                >
                  <div className="active-track-card-top">
                    <div>
                      <h4>{roadmap.name}</h4>
                      <p>{roadmap.category || 'Study Track'}</p>
                    </div>
                    <span className="active-track-progress-badge">{roadmap.progress_percent || 0}%</span>
                  </div>

                  <div className="active-track-progress-bar">
                    <div
                      className="active-track-progress-fill"
                      style={{ width: `${roadmap.progress_percent || 0}%`, backgroundColor: roadmap.color }}
                    />
                  </div>

                  <div className="active-track-session-meta">
                    <strong>{completedSessions}/{totalSessions} Sessions Completed</strong>
                    {roadmap.collaborators && roadmap.collaborators.length > 0 && (
                      <div className="active-track-collabs-badge font-body" style={{ marginTop: '6px', fontSize: '11px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#10B981' }}></span>
                        Collaborating: {roadmap.collaborators.map(c => c.user?.name).join(', ')}
                      </div>
                    )}
                  </div>

                  <div className="active-track-dates">
                    <div>
                      <span>Start</span>
                      <strong>{formatRoadmapDate(roadmap.start_date)}</strong>
                    </div>
                    <div>
                      <span>End</span>
                      <strong>{formatRoadmapDate(roadmap.end_date)}</strong>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 className="trail-main-title font-logo">
                {currentRoadmap ? currentRoadmap.name : 'Learning'} Path
              </h2>
              <div className="trail-tagline">
                <Sparkles size={14} className="sparkle" />
                <span>Click any node to view learning guides & resources</span>
              </div>
            </div>
            {currentRoadmap?.collaborators && currentRoadmap.collaborators.length > 0 && (
              <div className="trail-collabs-header font-body">
                <span className="collab-header-title">Collaborating:</span>
                <div className="collab-header-avatars">
                  {currentRoadmap.collaborators.map((c, cIdx) => (
                    <div key={cIdx} className="collab-header-avatar" title={`${c.user?.name || 'Collaborator'} (${c.status})`}>
                      <span className="collab-avatar-letter">
                        {c.user?.name ? c.user.name.charAt(0).toUpperCase() : '?'}
                      </span>
                      <span className={`collab-status-dot ${c.status}`}></span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </header>

        <div className="roadmap-trail-viewport">
          {currentRoadmap && currentRoadmap.sessions && currentRoadmap.sessions.length > 0 ? (
            <div className="trail-winding-scaffold">
              <div className="winding-nodes-list">
                {currentRoadmap.sessions.map((node, index) => {
                  const isEven = index % 2 === 0;
                  const sessionActionState = getSessionActionState(node);
                  const isCompleted = sessionActionState === 'completed';
                  const isActive = sessionActionState === 'active';
                  const isLocked = sessionActionState === 'locked';
                  const isUpcoming = sessionActionState === 'near' || sessionActionState === 'upcoming';
                  const isFocused = activeNode?.id === node.id;
                  const color = currentRoadmap.color;

                  return (
                    <div 
                      key={node.id} 
                      className={`trail-node-row ${isEven ? 'left-align' : 'right-align'}`}
                    >
                      <button 
                        type="button"
                        className={`trail-node-card ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''} ${isLocked ? 'locked' : ''} ${isUpcoming ? 'upcoming' : ''} ${isFocused ? 'focused' : ''}`}
                        onClick={() => handleNodeClick(node)}
                        style={{ borderLeft: `4px solid ${color}` }}
                      >
                        <div className="node-avatar-indicator">
                          <div className="indicator-pulse" style={{ backgroundColor: isActive ? color : (isLocked ? 'rgba(107, 114, 128, 0.2)' : 'transparent') }}></div>
                          <div className="indicator-core" style={{ backgroundColor: isCompleted ? '#22c55e' : (isActive ? color : (isLocked ? 'var(--color-text-secondary)' : 'var(--color-border)')) }}>
                            {isCompleted ? (
                              <CheckCircle size={16} color="white" />
                            ) : isLocked ? (
                              <Lock size={12} color="white" />
                            ) : null}
                          </div>
                        </div>

                        <div className="node-card-body">
                          <div className="node-card-heading">
                            <h4 className="node-title">{node.title}</h4>
                            <div className="node-state-badges">
                              {isLocked && <span className="state-pill locked">Locked</span>}
                              {isCompleted && <span className="state-pill completed">Completed</span>}
                              {node.status?.toLowerCase() === 'skipped' && <span className="state-pill skipped" style={{ backgroundColor: 'rgba(148, 163, 184, 0.12)', color: 'var(--color-text-secondary)' }}>Skipped</span>}
                              {isActive && <span className="state-pill available">Active</span>}
                              {!isLocked && !isCompleted && node.status?.toLowerCase() !== 'skipped' && !isActive && <span className="upcoming-card-label">Upcoming</span>}
                            </div>
                          </div>
                          <p className="node-desc-trimmed">{node.description || 'Topic Overview'}</p>
                          <div className="node-badges-row">
                            <span className="badge duration">{node.estimated_duration} min</span>
                            <span className="badge date">{node.scheduled_date}</span>
                            {isLocked && <span className="badge locked">Unlocks soon</span>}
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
              <button className="goto-chat-btn" onClick={() => navigate('/chat', { state: { initialPrompt: 'Create a study roadmap for me. Include sessions, durations, and suggested schedule.' } })}>
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

              {activeNode && selectedRoadmapId !== '1' && selectedRoadmapId !== '2' && (
                <div className="node-actions-container">
                  <span className="resource-section-lbl">Session Actions</span>
                  {(() => {
                    const sessionActionState = getSessionActionState(activeNode);

                    if (sessionActionState === 'locked' || sessionActionState === 'upcoming') {
                      return (
                        <div className="action-buttons-row">
                          <span className="upcoming-session-hint">This session is locked until it is within 24 hours of its scheduled time.</span>
                        </div>
                      );
                    }

                    if (sessionActionState === 'completed') {
                      return (
                        <div className="action-buttons-row">
                          <span className="upcoming-session-hint" style={{ color: '#22c55e' }}>✓ This topic has been completed.</span>
                        </div>
                      );
                    }

                    if (sessionActionState === 'skipped') {
                      return (
                        <div className="action-buttons-row">
                          <span className="upcoming-session-hint" style={{ color: 'var(--color-text-secondary)' }}>This topic was skipped.</span>
                          <button 
                            className="action-btn reschedule-btn"
                            onClick={() => handleUpdateSessionStatus('pending')}
                            style={{ marginLeft: '12px' }}
                          >
                            Restore Topic
                          </button>
                        </div>
                      );
                    }

                    // Otherwise it is 'near' or 'active' (less than 24 hours left, or past schedule)
                    return (
                      <div className="action-buttons-row">
                        <button 
                          className="action-btn complete-btn"
                          onClick={() => handleUpdateSessionStatus('completed')}
                        >
                          <CheckCircle size={14} /> Mark as Completed
                        </button>
                        <button 
                          className={`action-btn reschedule-btn ${showRescheduleDropdown ? 'active' : ''}`}
                          onClick={() => setShowRescheduleDropdown(!showRescheduleDropdown)}
                        >
                          <ChevronDown size={14} style={{ transform: showRescheduleDropdown ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} /> Reschedule
                        </button>
                        <button 
                          className="action-btn skip-btn"
                          onClick={() => handleUpdateSessionStatus('skipped')}
                        >
                          <Play size={14} /> Skip
                        </button>
                      </div>
                    );
                  })()}
                  
                  {/* Reschedule Dropdown */}
                  {showRescheduleDropdown && scheduleDates.length > 0 && (getSessionActionState(activeNode) === 'near' || getSessionActionState(activeNode) === 'active') && (
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
