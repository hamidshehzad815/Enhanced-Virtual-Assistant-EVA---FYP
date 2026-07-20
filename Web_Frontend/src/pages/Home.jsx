import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Calendar as CalendarIcon, Clock, CheckCircle2, Award, ChevronRight, Activity, ArrowUpRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useCalendar } from '../contexts/CalendarContext';
import apiRequest from '../services/api';
import './Home.css';

export const Home = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { dashboardData, fetchDashboard, toggleTask } = useCalendar();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotifDropdown, setShowNotifDropdown] = useState(false);

  const fetchNotifications = async () => {
    try {
      const response = await apiRequest('/api/notifications?limit=5');
      if (response.status === 'success' && response.data) {
        setNotifications(response.data.notifications || []);
        setUnreadCount(response.data.unread_count || 0);
      }
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
    }
  };

  const handleMarkAsRead = async (notifId) => {
    try {
      await apiRequest(`/api/notifications/${notifId}/read`, { method: 'PATCH' });
      fetchNotifications();
    } catch (err) {
      console.error('Failed to mark notification as read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiRequest('/api/notifications/read-all', { method: 'PATCH' });
      fetchNotifications();
    } catch (err) {
      console.error('Failed to mark all notifications as read:', err);
    }
  };

  useEffect(() => {
    fetchDashboard();
    fetchNotifications();

    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  const getGreeting = () => {
    const hours = new Date().getHours();
    if (hours < 12) return 'Good morning';
    if (hours < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const userName = user?.name || 'Areej';

  const upNext = dashboardData?.up_next
    ? {
        title: dashboardData.up_next.title,
        day: dashboardData.up_next.day || null,
        taskTime: dashboardData.up_next.time || null,
      }
    : null;

  const progressPercent = dashboardData?.daily_progress
    ? Math.round(dashboardData.daily_progress.completion_percentage)
    : 0;

  const learningList = Array.isArray(dashboardData?.learning)
    ? dashboardData.learning
        .filter(Boolean)
        .map((item) => ({
          title: item.title || 'Untitled learning goal',
          nextTopic: item.next_topic?.title || 'No upcoming topic',
          time: item.next_topic?.time || item.next_topic?.day || 'Pending',
        }))
    : [];

  const scheduleList = Array.isArray(dashboardData?.today_schedule)
    ? dashboardData.today_schedule
        .filter(Boolean)
        .map((item) => ({
          id: item.id || item._id || item.task_id || item.taskId,
          time: item.time || null,
          day: item.day || null,
          title: item.title || 'Untitled session',
          tag: item.display_status || item.status || 'pending',
          status: item.status || item.display_status || 'pending',
          editable: item.editable !== false,
        }))
    : [];

  const getTagColorClass = (tag) => {
    const normalizedTag = String(tag || 'pending').toLowerCase();

    switch (normalizedTag) {
      case 'completed':
      case 'complete':
        return 'tag-completed';
      case 'ongoing':
      case 'active':
        return 'tag-ongoing';
      case 'pending':
        return 'tag-pending';
      case 'due':
      case 'overdue':
        return 'tag-due';
      default:
        return 'tag-default';
    }
  };

  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progressPercent / 100) * circumference;

  return (
    <div className="home-screen animate-fade-in">
      <header className="home-dashboard-header">
        <div className="greeting-box">
          <span className="greeting-label">{getGreeting()},</span>
          <h2 className="user-name font-logo">{userName}</h2>
          <p className="dashboard-subtext">Here is your academic status overview for today.</p>
        </div>
        <div className="header-actions">
          <div style={{ position: 'relative' }}>
            <button 
              className="notif-btn"
              onClick={() => setShowNotifDropdown(!showNotifDropdown)}
            >
              <Bell size={18} />
              {unreadCount > 0 && <span className="notif-badge">{unreadCount}</span>}
            </button>

            {showNotifDropdown && (
              <div className="notif-dropdown">
                <div className="notif-dropdown-header">
                  <h4>Notifications</h4>
                  {unreadCount > 0 && (
                    <button className="mark-all-read-btn" onClick={handleMarkAllRead}>
                      Mark all as read
                    </button>
                  )}
                </div>
                <div className="notif-list">
                  {notifications.length > 0 ? (
                    notifications.map((notif) => (
                      <div 
                        key={notif._id} 
                        className={`notif-item ${!notif.is_read ? 'unread' : ''}`}
                        onClick={() => {
                          handleMarkAsRead(notif._id);
                          setShowNotifDropdown(false);
                        }}
                      >
                        <span className="notif-item-title">{notif.title}</span>
                        <span className="notif-item-msg">{notif.message}</span>
                        <span className="notif-item-time">
                          {new Date(notif.created_at || notif.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="empty-notifs">No notifications</div>
                  )}
                </div>
              </div>
            )}
          </div>
          <div className="user-profile-summary" onClick={() => navigate('/settings')}>
            <div className="summary-avatar">
              {userName.charAt(0).toUpperCase()}
            </div>
            <div className="summary-details">
              <span className="summary-name">{userName}</span>
              <span className="summary-role">Student</span>
            </div>
          </div>
        </div>
      </header>

      {/* Two Column Layout Grid */}
      <div className="dashboard-grid">
        {/* Main Left/Center Column */}
        <div className="grid-main-pane">
          {/* Current Focus section */}
          <div className="card-container">
            <div className="card-header-row">
              <div className="card-header-left">
                <Award size={18} className="header-icon focus-color" />
                <h3 className="card-title font-logo">Active Learning Focus</h3>
              </div>
              <button className="card-action-link" onClick={() => navigate('/roadmap')}>
                Manage Roadmaps <ChevronRight size={14} />
              </button>
            </div>

            <div className="focus-cards-grid">
              {learningList.length > 0 ? (
                learningList.map((item, idx) => (
                  <div key={idx} className="focus-bento-tile">
                    <div className="focus-tile-header">
                      <h4>{item.title}</h4>
                      <span className="time-badge">{item.time}</span>
                    </div>
                    <div className="focus-tile-detail">
                      <Clock size={13} className="sub-icon" />
                      <span>Next: <strong>{item.nextTopic}</strong></span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="font-body">No learning activity available from the backend yet.</p>
              )}
            </div>
          </div>

          {/* Today's Schedule Timeline */}
          <div className="card-container">
            <div className="card-header-row">
              <div className="card-header-left">
                <CalendarIcon size={18} className="header-icon schedule-color" />
                <h3 className="card-title font-logo">Today's Timeline</h3>
              </div>
              <button className="card-action-link" onClick={() => navigate('/calendar')}>
                Open Calendar <ChevronRight size={14} />
              </button>
            </div>

            <div className="timeline-wrapper">
              {scheduleList.length > 0 ? (
                scheduleList.map((item, idx) => {
                  const normalizedTag = String(item.tag || 'pending').toLowerCase();

                  return (
                    <div key={idx} className="timeline-item">
                      <div className="timeline-time-col font-body">
                        {item.time || item.day || 'All day'}
                      </div>
                      <div className="timeline-node">
                        <div className={`timeline-dot-core ${normalizedTag}`}></div>
                      </div>
                              <div className="timeline-content-col">
                              <div className="timeline-event-card">
                                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                  <span className="event-title">{item.title}</span>
                                  <span className={`schedule-tag font-body ${getTagColorClass(item.tag)}`}>
                                    {String(item.tag || 'pending').toUpperCase()}
                                  </span>
                                </div>
                                <button
                                  className="timeline-complete-btn"
                                  onClick={() => toggleTask(item.id, item.status)}
                                  disabled={!item.editable}
                                  aria-label={item.status === 'complete' || item.status === 'completed' ? 'Mark as pending' : 'Mark as complete'}
                                >
                                  <CheckCircle2 size={16} />
                                </button>
                              </div>
                            </div>
                    </div>
                  );
                })
              ) : (
                <p className="font-body">No timeline sessions returned by the backend for this user.</p>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar Right Column */}
        <div className="grid-side-pane">
          {/* Progress Circular Dial */}
          <div className="card-container side-card progress-card">
            <div className="side-card-header">
              <Activity size={16} />
              <span>Completion Velocity</span>
            </div>
            
            <div className="progress-gauge-container">
              <svg className="progress-ring" width="140" height="140">
                <circle
                  className="progress-ring-track"
                  strokeWidth="8"
                  fill="transparent"
                  r={radius}
                  cx="70"
                  cy="70"
                />
                <circle
                  className="progress-ring-indicator"
                  strokeWidth="8"
                  fill="transparent"
                  r={radius}
                  cx="70"
                  cy="70"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                />
              </svg>
              <div className="progress-text-overlay">
                <span className="percent-text font-body">{progressPercent}%</span>
                <span className="label-text">completed</span>
              </div>
            </div>

            <div className="progress-stats-box">
              <p className="progress-cheer">
                {progressPercent >= 100 
                  ? "Outstanding! You completed all scheduled tasks." 
                  : `Keep going! You're ${progressPercent}% done with today's goal.`}
              </p>
            </div>
          </div>

          {/* Up Next / Next Event Card */}
          <div className="card-container side-card up-next-card">
            <div className="side-card-header">
              <Clock size={16} />
              <span>Next Critical Milestone</span>
            </div>
            
            <div className="up-next-core">
              <h4 className="up-next-title">{upNext?.title || 'No upcoming task'}</h4>
              <div className="up-next-details">
                <span className="detail-pill day">{upNext?.day || 'No date'}</span>
                <span className="detail-pill time">{upNext?.taskTime || 'No time'}</span>
              </div>
            </div>

            <button className="btn btn-primary btn-remind-saas" onClick={() => alert('Reminder set!')}>
              Set Quick Reminder <ArrowUpRight size={14} style={{ marginLeft: '4px' }} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
