import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, Calendar as CalendarIcon, Clock, CheckCircle2, Award, ChevronRight, Activity, ArrowUpRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useCalendar } from '../contexts/CalendarContext';
import './Home.css';

export const Home = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { dashboardData, fetchDashboard } = useCalendar();

  useEffect(() => {
    fetchDashboard();
  }, []);

  const getGreeting = () => {
    const hours = new Date().getHours();
    if (hours < 12) return 'Good morning';
    if (hours < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const userName = user?.name || 'Areej';

  // Fallbacks
  const fallbackUpNext = {
    title: 'NLP Mid Exam',
    day: 'Thursday',
    taskTime: '3:00 PM',
  };

  const fallbackProgress = {
    completed_tasks: 3,
    total_tasks: 5,
    completion_percentage: 60
  };

  const fallbackLearning = [
    {
      title: 'Python Roadmap',
      nextTopic: 'OOP Concepts',
      time: '04:30 PM'
    },
    {
      title: 'Flutter Animations',
      nextTopic: 'CustomPaint',
      time: '07:15 PM'
    }
  ];

  const fallbackSchedule = [
    { time: '08:00 AM', title: 'Math Lecture', tag: 'completed' },
    { time: '10:00 AM', title: 'Intro to AI', tag: 'pending' },
    { time: '01:00 PM', title: 'Physics Lab', tag: 'ongoing' },
    { time: '03:30 PM', title: 'Group Study', tag: 'due' },
    { time: '05:00 PM', title: 'NLP Exam Prep', tag: 'pending' }
  ];

  const upNext = dashboardData?.up_next ? {
    title: dashboardData.up_next.title,
    day: dashboardData.up_next.day || 'Today',
    taskTime: dashboardData.up_next.time || 'All day'
  } : fallbackUpNext;

  const progressPercent = dashboardData?.daily_progress 
    ? Math.round(dashboardData.daily_progress.completion_percentage) 
    : fallbackProgress.completion_percentage;

  const learningList = dashboardData?.learning && dashboardData.learning.length > 0 
    ? dashboardData.learning.map(item => ({
        title: item.title,
        nextTopic: item.next_topic?.title || 'No upcoming topic',
        time: item.next_topic?.time || 'Pending'
      })) 
    : fallbackLearning;

  const scheduleList = dashboardData?.today_schedule && dashboardData.today_schedule.length > 0
    ? dashboardData.today_schedule.map(item => ({
        time: item.time || 'All day',
        title: item.title,
        tag: item.display_status || item.status
      }))
    : fallbackSchedule;

  const getTagColorClass = (tag) => {
    switch (tag.toLowerCase()) {
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
          <button className="notif-btn">
            <Bell size={18} />
          </button>
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
              {learningList.map((item, idx) => (
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
              ))}
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
              {scheduleList.map((item, idx) => (
                <div key={idx} className="timeline-item">
                  <div className="timeline-time-col font-body">{item.time}</div>
                  <div className="timeline-node">
                    <div className={`timeline-dot-core ${item.tag.toLowerCase()}`}></div>
                  </div>
                  <div className="timeline-content-col">
                    <div className="timeline-event-card">
                      <span className="event-title">{item.title}</span>
                      <span className={`schedule-tag font-body ${getTagColorClass(item.tag)}`}>
                        {item.tag.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
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
              <h4 className="up-next-title">{upNext.title}</h4>
              <div className="up-next-details">
                <span className="detail-pill day">{upNext.day}</span>
                <span className="detail-pill time">{upNext.taskTime}</span>
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
