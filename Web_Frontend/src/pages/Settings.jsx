import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Palette, Globe, RefreshCw, Bell, BellOff, Mail, Moon, Clock, 
  Flag, Timer, Award, Shield, Info, LogOut, Trash2, Plus, X, Edit, Check, Settings as SettingsIcon, User
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useSettings } from '../contexts/SettingsContext';
import './Settings.css';

export const Settings = () => {
  const navigate = useNavigate();
  const { user, logout, updateProfile, checkAuth } = useAuth();
  const { 
    settings, 
    learningSchedules, 
    updateSettings, 
    addSchedule, 
    updateSchedule, 
    deleteSchedule 
  } = useSettings();

  // Selected Category (for tabbed view on desktop)
  const [activeCategory, setActiveCategory] = useState('profile');
  
  // Profile edit states
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [profileName, setProfileName] = useState(user?.name || '');
  const [profileEmail, setProfileEmail] = useState(user?.email || '');

  useEffect(() => {
    setProfileName(user?.name || '');
    setProfileEmail(user?.email || '');
  }, [user]);

  // Forms
  const [newQuietHour, setNewQuietHour] = useState({ label: 'Sleep Time', start: '22:00', end: '07:00', enabled: true });
  const [newScheduleForm, setNewScheduleForm] = useState({ label: 'Weekday Slot', slots: [{ day_of_week: 1, start_time: '16:00', duration_minutes: 90 }] });

  const handleProfileSave = async (e) => {
    e.preventDefault();
    const res = await updateProfile({ name: profileName });
    if (res.success) {
      setIsEditingProfile(false);
      alert('Profile updated successfully!');
    } else {
      alert(res.message || 'Failed to update profile');
    }
  };

  const handleLogoutClick = () => {
    if (window.confirm('Are you sure you want to log out?')) {
      logout();
      navigate('/welcome');
    }
  };

  const handleDeleteAccountClick = () => {
    if (window.confirm('CAUTION: This will permanently delete your account and all data. This cannot be undone. Are you absolutely sure?')) {
      alert('Account deletion requested. Please contact administrator.');
    }
  };

  const handleAddQuietHour = () => {
    const list = [...(settings.quiet_hours || []), newQuietHour];
    updateSettings({ quiet_hours: list });
    alert('Interval added!');
  };

  const handleRemoveQuietHour = (idx) => {
    const list = (settings.quiet_hours || []).filter((_, i) => i !== idx);
    updateSettings({ quiet_hours: list });
  };

  const handleCreateSchedule = async () => {
    if (!newScheduleForm.label.trim()) {
      alert('Schedule label is required');
      return;
    }
    // Convert frontend form shape to backend-expected payload
    // Backend expects: { label, slots: [{ day: number (0=Mon), time: 'HH:mm', duration_minutes: number }] }
    const payload = {
      label: String(newScheduleForm.label || '').trim(),
      slots: (Array.isArray(newScheduleForm.slots) ? newScheduleForm.slots : []).map(s => ({
        day: Number(s.day_of_week ?? s.day),
        time: String((s.start_time ?? s.time) || '').trim(),
        duration_minutes: Number(s.duration_minutes ?? s.durationMinutes ?? 0)
      }))
    };
    const res = await addSchedule(payload);
    if (res.success) {
      alert('Schedule created!');
      setNewScheduleForm({ label: 'Weekday Slot', slots: [{ day_of_week: 1, start_time: '16:00', duration_minutes: 90 }] });
    } else {
      alert(res.message || 'Failed to create schedule');
    }
  };

  const handleRemoveSchedule = async (id) => {
    if (!window.confirm('Delete this schedule slot?')) return;
    const res = await deleteSchedule(id);
    if (!res.success) {
      alert(res.message || 'Could not delete schedule');
    }
  };

  const getDayName = (dayNum) => {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return days[dayNum] || 'Monday';
  };

  const initials = user?.name ? user.name.charAt(0).toUpperCase() : 'A';

  return (
    <div className="settings-workspace animate-fade-in">
      
      {/* 1. Left Sidebar: Settings Categories Nav */}
      <div className="settings-left-pane">
        <div className="pane-header-container">
          <SettingsIcon size={20} className="pane-icon" />
          <h3 className="pane-title font-logo">Settings</h3>
        </div>

        {/* Profile Card Header */}
        <div className="settings-profile-summary">
          <div className="settings-avatar-circle" style={{ position: 'relative' }}>
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt="avatar" style={{ width: '100%', height: '100%', borderRadius: '50%' }} />
            ) : initials}
            <button
              className="avatar-edit-btn"
              title="Edit avatar"
              onClick={() => document.getElementById('avatar-file-input')?.click()}
              style={{ position: 'absolute', right: -6, bottom: -6 }}
            >
              <Edit size={14} />
            </button>
            <input id="avatar-file-input" type="file" accept="image/*" style={{ display: 'none' }} onChange={async (e) => {
              const file = e.target.files && e.target.files[0];
              if (!file) return;
              const token = localStorage.getItem('access_token');
              const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
              const url = `${baseUrl}/api/profile/avatar`;
              const form = new FormData();
              form.append('avatar', file);
              try {
                const res = await fetch(url, {
                  method: 'POST',
                  headers: token ? { Authorization: `Bearer ${token}` } : {},
                  body: form
                });
                if (!res.ok) throw new Error('Upload failed');
                // Refresh profile
                if (checkAuth) await checkAuth();
                alert('Avatar updated');
              } catch (err) {
                console.error('Avatar upload failed', err);
                alert('Failed to upload avatar. Please try again.');
              }
            }} />
          </div>
          <div className="settings-profile-details">
            <h4>{user?.name || 'Areej'}</h4>
            <p>@{user?.username || 'username'}</p>
          </div>
        </div>

        <nav className="settings-category-menu">
          <button 
            className={`settings-cat-btn ${activeCategory === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveCategory('profile')}
          >
            <User size={16} />
            <span>Profile Identity</span>
          </button>
          
          <button 
            className={`settings-cat-btn ${activeCategory === 'preferences' ? 'active' : ''}`}
            onClick={() => setActiveCategory('preferences')}
          >
            <Palette size={16} />
            <span>App Preferences</span>
          </button>

          <button 
            className={`settings-cat-btn ${activeCategory === 'notifications' ? 'active' : ''}`}
            onClick={() => setActiveCategory('notifications')}
          >
            <Bell size={16} />
            <span>Alerts & Quiet Hours</span>
          </button>

          <button 
            className={`settings-cat-btn ${activeCategory === 'tasks' ? 'active' : ''}`}
            onClick={() => setActiveCategory('tasks')}
          >
            <Flag size={16} />
            <span>Task Priorities</span>
          </button>

          <button 
            className={`settings-cat-btn ${activeCategory === 'study' ? 'active' : ''}`}
            onClick={() => setActiveCategory('study')}
          >
            <Award size={16} />
            <span>Study Schedules</span>
          </button>

          <button 
            className={`settings-cat-btn ${activeCategory === 'privacy' ? 'active' : ''}`}
            onClick={() => setActiveCategory('privacy')}
          >
            <Shield size={16} />
            <span>Security & Danger</span>
          </button>
        </nav>
      </div>

      {/* 2. Right Pane: Detailed Form Viewports */}
      <div className="settings-center-pane">
        
        {/* TAB A: PROFILE IDENTITY */}
        {activeCategory === 'profile' && (
          <div className="settings-details-panel">
            <h2 className="panel-title font-logo">Profile Identity</h2>
            <p className="panel-subtitle">Manage your personal credentials, display name, and login email address.</p>

            <div className="settings-card-saas">
              {isEditingProfile ? (
                <form onSubmit={handleProfileSave} className="profile-edit-saas-form">
                  <div className="input-group">
                    <label className="input-label">Full Name</label>
                    <input
                      type="text"
                      className="input-field"
                      value={profileName}
                      onChange={(e) => setProfileName(e.target.value)}
                      required
                    />
                  </div>
                  <div className="input-group">
                    <label className="input-label">Email Address</label>
                    <input
                      type="email"
                      className="input-field"
                      value={profileEmail}
                      disabled
                    />
                  </div>
                  <div className="profile-form-actions">
                    <button type="button" className="btn btn-outlined cancel-btn" onClick={() => setIsEditingProfile(false)}>
                      Cancel
                    </button>
                    <button type="submit" className="btn btn-primary save-btn">
                      Save Profile
                    </button>
                  </div>
                </form>
              ) : (
                <div className="profile-identity-display">
                  <div className="identity-avatar">{initials}</div>
                  <div className="identity-info">
                    <h4>{user?.name || 'Areej'}</h4>
                    <p className="username">@{user?.username || 'areej_student'}</p>
                    <p className="email">{user?.email || 'student@domain.com'}</p>
                  </div>
                  <button className="edit-identity-btn" onClick={() => setIsEditingProfile(true)}>
                    <Edit size={14} /> Edit Identity
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB B: APP PREFERENCES */}
        {activeCategory === 'preferences' && (
          <div className="settings-details-panel">
            <h2 className="panel-title font-logo">App Preferences</h2>
            <p className="panel-subtitle">Customize application visual theme, language locale settings, and external calendar integrations.</p>

            <div className="settings-card-saas flex-column">
              {/* Theme Selector */}
              <div className="settings-saas-row">
                <div className="row-meta">
                  <span className="row-title">Visual Theme Mode</span>
                  <p className="row-desc">Switch between light mode, dark mode, or follow system default.</p>
                </div>
                <select
                  value={settings.theme}
                  onChange={(e) => updateSettings({ theme: e.target.value })}
                  className="row-select font-body"
                >
                  <option value="light">Light Theme</option>
                  <option value="dark">Dark Theme</option>
                  <option value="system">System Preference</option>
                </select>
              </div>

              {/* Language Selector */}
              <div className="settings-saas-row border-top">
                <div className="row-meta">
                  <span className="row-title">Language (Localization)</span>
                  <p className="row-desc">English is the only supported interface language for this release.</p>
                </div>
                <select
                  value="en"
                  disabled
                  className="row-select font-body"
                >
                  <option value="en">English (EN)</option>
                </select>
              </div>
              {/* Google Calendar Sync */}
              <div className="settings-saas-row border-top">
                <div className="row-meta">
                  <span className="row-title">Google Calendar Integration</span>
                  <p className="row-desc">Synchronize study schedules and timelines automatically with Google calendar.</p>
                </div>
                <label className="toggle-switch-saas">
                  <input
                    type="checkbox"
                    checked={settings.google_calendar_sync_enabled}
                    onChange={(e) => updateSettings({ google_calendar_sync_enabled: e.target.checked })}
                  />
                  <span className="toggle-slider-saas" />
                </label>
              </div>
            </div>
          </div>
        )}

        {/* TAB C: ALERTS & QUIET HOURS */}
        {activeCategory === 'notifications' && (
          <div className="settings-details-panel">
            <h2 className="panel-title font-logo">Alerts & Quiet Hours</h2>
            <p className="panel-subtitle">Toggle study notifications and configure quiet hour blocks to block notifications.</p>

            <div className="settings-card-saas flex-column">
              {/* Master alerts switch */}
              <div className="settings-saas-row">
                <div className="row-meta">
                  <span className="row-title">Master Notifications Alert</span>
                  <p className="row-desc">Master switch to enable or disable all notifications and summaries.</p>
                </div>
                <label className="toggle-switch-saas">
                  <input
                    type="checkbox"
                    checked={settings.notifications_enabled}
                    onChange={(e) => updateSettings({ notifications_enabled: e.target.checked })}
                  />
                  <span className="toggle-slider-saas" />
                </label>
              </div>

              {/* Push alerts */}
              <div className="settings-saas-row border-top">
                <div className="row-meta">
                  <span className="row-title">Push Notifications</span>
                  <p className="row-desc">Enable push popups on tasks, schedules, and roadmaps.</p>
                </div>
                <label className="toggle-switch-saas">
                  <input
                    type="checkbox"
                    checked={settings.push_notifications_enabled}
                    onChange={(e) => updateSettings({ push_notifications_enabled: e.target.checked })}
                  />
                  <span className="toggle-slider-saas" />
                </label>
              </div>

              {/* Email alerts */}
              <div className="settings-saas-row border-top">
                <div className="row-meta">
                  <span className="row-title">Email Reports</span>
                  <p className="row-desc">Send study guides, digests, and reports straight to your inbox.</p>
                </div>
                <label className="toggle-switch-saas">
                  <input
                    type="checkbox"
                    checked={settings.email_notifications_enabled}
                    onChange={(e) => updateSettings({ email_notifications_enabled: e.target.checked })}
                  />
                  <span className="toggle-slider-saas" />
                </label>
              </div>

              {/* Default reminder */}
              <div className="settings-saas-row border-top">
                <div className="row-meta">
                  <span className="row-title">Default Reminder Lead time</span>
                  <p className="row-desc">Select how many minutes before task execution to trigger notification.</p>
                </div>
                <select
                  value={settings.default_reminder_minutes}
                  onChange={(e) => updateSettings({ default_reminder_minutes: Number(e.target.value) })}
                  className="row-select font-body"
                >
                  <option value="5">5 minutes before</option>
                  <option value="15">15 minutes before</option>
                  <option value="30">30 minutes before</option>
                  <option value="60">60 minutes before</option>
                </select>
              </div>
            </div>

            {/* Quiet Hours inline CRUD section */}
            <div className="inline-crud-container">
              <h3 className="inline-crud-title font-logo">Quiet Hours Slots</h3>
              
              <div className="settings-card-saas quiet-hour-crud">
                <div className="crud-header">
                  <span>Define Quiet Interval</span>
                </div>
                <div className="crud-add-form-saas">
                  <input
                    type="text"
                    placeholder="e.g. Bedtime Study Block"
                    value={newQuietHour.label}
                    onChange={(e) => setNewQuietHour(prev => ({ ...prev, label: e.target.value }))}
                    className="crud-text-field"
                  />
                  <div className="time-pickers-row">
                    <input
                      type="time"
                      value={newQuietHour.start}
                      onChange={(e) => setNewQuietHour(prev => ({ ...prev, start: e.target.value }))}
                      className="crud-time-picker"
                    />
                    <span className="separator">to</span>
                    <input
                      type="time"
                      value={newQuietHour.end}
                      onChange={(e) => setNewQuietHour(prev => ({ ...prev, end: e.target.value }))}
                      className="crud-time-picker"
                    />
                  </div>
                  <button className="crud-add-btn" onClick={handleAddQuietHour}>
                    <Plus size={16} style={{ marginRight: '4px' }} /> Add Slot
                  </button>
                </div>

                <div className="crud-list-saas border-top">
                  <span className="list-subtitle">Active Silent Blocks</span>
                  {(settings.quiet_hours || []).length > 0 ? (
                    <div className="quiet-hours-grid-list">
                      {settings.quiet_hours.map((qh, idx) => (
                        <div key={idx} className="quiet-hour-tile-saas">
                          <div className="tile-left">
                            <strong>{qh.label}</strong>
                            <span>{qh.start} - {qh.end}</span>
                          </div>
                          <button className="tile-delete-btn" onClick={() => handleRemoveQuietHour(idx)}>
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="no-items-lbl">No quiet hours blocks defined.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB D: TASK SCHEDULING RULES */}
        {activeCategory === 'tasks' && (
          <div className="settings-details-panel">
            <h2 className="panel-title font-logo">Task Scheduling Rules</h2>
            <p className="panel-subtitle">Configure defaults priorities and task study durations when creating tasks via AI.</p>

            <div className="settings-card-saas flex-column">
              {/* Default Priority */}
              <div className="settings-saas-row">
                <div className="row-meta">
                  <span className="row-title">Default Task Priority</span>
                  <p className="row-desc">Specify the default priority assigned to newly created tasks.</p>
                </div>
                <select
                  value={settings.default_task_priority}
                  onChange={(e) => updateSettings({ default_task_priority: e.target.value })}
                  className="row-select font-body"
                >
                  <option value="low">Low Priority</option>
                  <option value="medium">Medium Priority</option>
                  <option value="high">High Priority</option>
                </select>
              </div>

              {/* Default Duration */}
              <div className="settings-saas-row border-top">
                <div className="row-meta">
                  <span className="row-title">Default Study Duration</span>
                  <p className="row-desc">Specify the duration allocated to custom study tasks generated in plans.</p>
                </div>
                <select
                  value={settings.default_task_duration}
                  onChange={(e) => updateSettings({ default_task_duration: Number(e.target.value) })}
                  className="row-select font-body"
                >
                  <option value="30">30 minutes</option>
                  <option value="60">60 minutes (1 hour)</option>
                  <option value="90">90 minutes (1.5 hours)</option>
                  <option value="120">120 minutes (2 hours)</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* TAB E: STUDY SCHEDULING SLOTS */}
        {activeCategory === 'study' && (
          <div className="settings-details-panel">
            <h2 className="panel-title font-logo">Learning Study Slots</h2>
            <p className="panel-subtitle">Configure study templates directory and schedule slots routines for roadmaps generation.</p>

            <div className="inline-crud-container" style={{ marginTop: 0 }}>
              <div className="settings-card-saas study-schedule-crud">
                <div className="crud-header">
                  <span>Create Routine Template Slot</span>
                </div>
                <div className="study-slots-form">
                  <div className="input-group">
                    <label className="input-label">Template Label Name</label>
                    <input
                      type="text"
                      className="input-field"
                      value={newScheduleForm.label}
                      onChange={(e) => setNewScheduleForm(prev => ({ ...prev, label: e.target.value }))}
                      placeholder="e.g. Weekend Focus routine"
                    />
                  </div>
                  <div className="study-form-row">
                    <select
                      value={newScheduleForm.slots[0].day_of_week}
                      onChange={(e) => {
                        const day = Number(e.target.value);
                        setNewScheduleForm(prev => {
                          const slots = [...prev.slots];
                          slots[0].day_of_week = day;
                          return { ...prev, slots };
                        });
                      }}
                      className="study-form-select"
                    >
                      <option value="1">Monday</option>
                      <option value="2">Tuesday</option>
                      <option value="3">Wednesday</option>
                      <option value="4">Thursday</option>
                      <option value="5">Friday</option>
                      <option value="6">Saturday</option>
                      <option value="0">Sunday</option>
                    </select>

                    <input
                      type="time"
                      value={newScheduleForm.slots[0].start_time}
                      onChange={(e) => {
                        const time = e.target.value;
                        setNewScheduleForm(prev => {
                          const slots = [...prev.slots];
                          slots[0].start_time = time;
                          return { ...prev, slots };
                        });
                      }}
                      className="study-form-time"
                    />

                    <select
                      value={newScheduleForm.slots[0].duration_minutes}
                      onChange={(e) => {
                        const dur = Number(e.target.value);
                        setNewScheduleForm(prev => {
                          const slots = [...prev.slots];
                          slots[0].duration_minutes = dur;
                          return { ...prev, slots };
                        });
                      }}
                      className="study-form-select"
                    >
                      <option value="30">30 min</option>
                      <option value="60">60 min</option>
                      <option value="90">90 min</option>
                      <option value="120">120 min</option>
                    </select>

                    <button className="crud-add-btn study-add-btn" onClick={handleCreateSchedule}>
                      <Plus size={16} /> Create
                    </button>
                  </div>
                </div>

                <div className="crud-list-saas border-top">
                  <span className="list-subtitle">Configured Schedules Directory</span>
                      {learningSchedules.length > 0 ? (
                        <div className="schedules-grid-list-saas">
                          {learningSchedules.map((sched) => (
                            <div key={sched.id} className="schedule-tile-saas">
                              <div className="sched-left">
                                <strong>{sched.label}</strong>
                                {sched.slots && sched.slots.map((s, i) => {
                                  const dayNum = (s.day_of_week !== undefined && s.day_of_week !== null) ? s.day_of_week : (s.day !== undefined ? s.day : null);
                                  const timeStr = (s.start_time ?? s.time) || '';
                                  const dur = s.duration_minutes ?? s.durationMinutes ?? '';
                                  return (
                                    <span key={i} className="sched-slot-span">
                                      {getDayName(dayNum)} at {timeStr} ({dur} mins)
                                    </span>
                                  );
                                })}
                              </div>
                              <button className="tile-delete-btn" onClick={() => handleRemoveSchedule(sched.id)}>
                                <Trash2 size={14} />
                              </button>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="no-items-lbl">No custom learning schedule slots defined.</p>
                      )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB F: PRIVACY & DANGER ZONE */}
        {activeCategory === 'privacy' && (
          <div className="settings-details-panel">
            <h2 className="panel-title font-logo">Security & Privacy</h2>
            <p className="panel-subtitle">Configure social collaboration permissions and manage account states.</p>

            <div className="settings-card-saas flex-column">
              {/* Allow Friend Requests */}
              <div className="settings-saas-row">
                <div className="row-meta">
                  <span className="row-title">Allow Friend Invites</span>
                  <p className="row-desc">Choose who is allowed to send you buddies collaboration invites.</p>
                </div>
                <select
                  value={settings.allow_friend_requests}
                  onChange={(e) => updateSettings({ allow_friend_requests: e.target.value })}
                  className="row-select font-body"
                >
                  <option value="everyone">Everyone</option>
                  <option value="friends">Friends of Friends</option>
                  <option value="nobody">Nobody</option>
                </select>
              </div>

              {/* Version */}
              <div className="settings-saas-row border-top">
                <div className="row-meta">
                  <span className="row-title">Product Version Info</span>
                  <p className="row-desc">Current client bundle build versions.</p>
                </div>
                <span className="version-info-badge">v2.0 Web Platform</span>
              </div>
            </div>

            <div className="danger-zone-saas">
              <h3 className="danger-zone-title font-logo">Danger Zone</h3>
              
              <div className="settings-card-saas danger-card-saas flex-column">
                <div className="settings-saas-row">
                  <div className="row-meta">
                    <span className="row-title danger">Sign Out Session</span>
                    <p className="row-desc">Terminate active session credentials and return to welcome page.</p>
                  </div>
                  <button className="danger-zone-action-btn" onClick={handleLogoutClick}>
                    Log Out <LogOut size={14} style={{ marginLeft: '6px' }} />
                  </button>
                </div>

                <div className="settings-saas-row border-top">
                  <div className="row-meta">
                    <span className="row-title danger">Delete Academic Profile</span>
                    <p className="row-desc">Permanently wipe user info, calendar items, logs, and roadmaps.</p>
                  </div>
                  <button className="danger-zone-action-btn delete" onClick={handleDeleteAccountClick}>
                    Delete Account <Trash2 size={14} style={{ marginLeft: '6px' }} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

    </div>
  );
};

export default Settings;
