import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Palette, Globe, RefreshCw, Bell, BellOff, Mail, Moon, Clock, 
  Flag, Timer, Award, Shield, Info, LogOut, Trash2, Plus, X, Edit, Check, Settings as SettingsIcon, User
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useSettings } from '../contexts/SettingsContext';
import apiRequest from '../services/api';
import './Settings.css';

export const Settings = () => {
  const navigate = useNavigate();
  const { user, logout, updateProfile, checkAuth, updateUserSnapshot } = useAuth();
  const { 
    settings, 
    learningSchedules, 
    updateSettings, 
    addSchedule, 
    updateSchedule, 
    deleteSchedule,
    fetchSettings
  } = useSettings();

  // Selected Category (for tabbed view on desktop)
  const [activeCategory, setActiveCategory] = useState('profile');
  
  // Profile edit states
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [profileName, setProfileName] = useState(user?.name || '');
  const [profileEmail, setProfileEmail] = useState(user?.email || '');
  const [avatarPreview, setAvatarPreview] = useState(user?.avatar_url || user?.profile_picture || '');

  const [googleCalendarConnected, setGoogleCalendarConnected] = useState(false);

  const fetchIntegrationStatus = async () => {
    try {
      const res = await apiRequest('/api/integrations');
      if (res.status === 'success' && Array.isArray(res.data)) {
        const hasGoogle = res.data.some(
          (item) => item.provider === 'google_calendar' && item.is_active === true
        );
        setGoogleCalendarConnected(hasGoogle);
      } else {
        setGoogleCalendarConnected(false);
      }
    } catch (err) {
      console.warn('Failed to fetch integrations list:', err);
      setGoogleCalendarConnected(false);
    }
  };

  useEffect(() => {
    fetchIntegrationStatus();
  }, []);

  useEffect(() => {
    setProfileName(user?.name || '');
    setProfileEmail(user?.email || '');
    setAvatarPreview(user?.avatar_url || user?.profile_picture || '');
  }, [user]);

  // Forms
  const [newQuietHour, setNewQuietHour] = useState({ label: 'Sleep Time', start: '22:00', end: '07:00', enabled: true });
  // day_of_week uses the backend/mobile/AI-server convention: 0=Monday … 6=Sunday
  const emptySlot = () => ({ day_of_week: 0, start_time: '16:00', duration_minutes: 90 });
  const [newScheduleForm, setNewScheduleForm] = useState({ label: 'Weekday Slot', slots: [emptySlot()] });
  const [editingScheduleId, setEditingScheduleId] = useState(null);

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

  const handleAvatarUpload = async (e) => {
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
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.message || 'Upload failed');
      const nextAvatarUrl = data?.data?.user?.avatar_url || data?.data?.user?.profile_picture || data?.user?.avatar_url || data?.user?.profile_picture || data?.avatar_url || data?.profile_picture || '';
      if (nextAvatarUrl) {
        setAvatarPreview(nextAvatarUrl);
        if (updateUserSnapshot) updateUserSnapshot({ avatar_url: nextAvatarUrl, profile_picture: nextAvatarUrl });
      }
      if (checkAuth) await checkAuth();
      alert('Avatar updated');
    } catch (err) {
      console.error('Avatar upload failed', err);
      alert('Failed to upload avatar. Please try again.');
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

  const handleQuietHoursEnabledToggle = (enabled) => {
    updateSettings({ quiet_hours_enabled: enabled });
  };

  const handleAddSlotRow = () => {
    setNewScheduleForm(prev => ({ ...prev, slots: [...prev.slots, emptySlot()] }));
  };

  const handleRemoveSlotRow = (idx) => {
    setNewScheduleForm(prev => ({
      ...prev,
      slots: prev.slots.length > 1 ? prev.slots.filter((_, i) => i !== idx) : prev.slots
    }));
  };

  const handleSlotFieldChange = (idx, field, value) => {
    setNewScheduleForm(prev => {
      const slots = prev.slots.map((s, i) => (i === idx ? { ...s, [field]: value } : s));
      return { ...prev, slots };
    });
  };

  const handleEditScheduleClick = (sched) => {
    setEditingScheduleId(sched.id);
    setNewScheduleForm({
      label: sched.label || '',
      slots: (Array.isArray(sched.slots) && sched.slots.length > 0
        ? sched.slots
        : [{}]
      ).map(s => ({
        day_of_week: Number(s.day_of_week ?? s.day ?? 0),
        start_time: String((s.start_time ?? s.time) || '16:00'),
        duration_minutes: Number(s.duration_minutes ?? s.durationMinutes ?? 90)
      }))
    });
  };

  const handleCancelEditSchedule = () => {
    setEditingScheduleId(null);
    setNewScheduleForm({ label: 'Weekday Slot', slots: [emptySlot()] });
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

    // Helper: Convert time string "HH:mm" to minutes from midnight
    const parseTimeToMinutes = (timeStr) => {
      const [h, m] = timeStr.split(':').map(Number);
      return h * 60 + m;
    };

    // Helper: Check if two time intervals overlap (supporting midnight wrapping)
    const timesOverlap = (start1, end1, start2, end2) => {
      const splitInterval = (start, end) => {
        if (end <= start) {
          return [[start, 1440], [0, end]];
        }
        return [[start, end]];
      };

      const intervals1 = splitInterval(start1, end1);
      const intervals2 = splitInterval(start2, end2);

      for (const [s1, e1] of intervals1) {
        for (const [s2, e2] of intervals2) {
          if (Math.max(s1, s2) < Math.min(e1, e2)) {
            return true;
          }
        }
      }
      return false;
    };

    // Validate that the new study slot does not overlap with any active quiet hours
    // (only when quiet hours are actually enabled — matches the backend's own gating,
    // which treats quiet_hours as inert unless quiet_hours_enabled is true)
    const quietHours = settings.quiet_hours_enabled ? (settings.quiet_hours || []) : [];
    const hasOverlap = payload.slots.some(slot => {
      const studyStart = parseTimeToMinutes(slot.time);
      const studyEndVal = (studyStart + slot.duration_minutes) % 1440;

      return quietHours.some(qh => {
        if (qh.enabled === false) return false;
        const qhStart = parseTimeToMinutes(qh.start);
        const qhEnd = parseTimeToMinutes(qh.end);
        return timesOverlap(studyStart, studyEndVal, qhStart, qhEnd);
      });
    });

    if (hasOverlap) {
      alert("Error: This study schedule slot conflicts with your defined Quiet Hours/Sleep Time. Please choose a different time.");
      return;
    }

    const res = editingScheduleId
      ? await updateSchedule(editingScheduleId, payload)
      : await addSchedule(payload);

    if (res.success) {
      alert(editingScheduleId ? 'Schedule updated!' : 'Schedule created!');
      setEditingScheduleId(null);
      setNewScheduleForm({ label: 'Weekday Slot', slots: [emptySlot()] });
    } else {
      alert(res.message || (editingScheduleId ? 'Failed to update schedule' : 'Failed to create schedule'));
    }
  };

  const handleRemoveSchedule = async (id) => {
    if (!window.confirm('Delete this schedule slot?')) return;
    const res = await deleteSchedule(id);
    if (!res.success) {
      alert(res.message || 'Could not delete schedule');
    } else if (editingScheduleId === id) {
      handleCancelEditSchedule();
    }
  };

  const handleMasterNotificationToggle = async (enabled) => {
    const notificationFields = {
      notifications_enabled: enabled,
      push_notifications_enabled: enabled,
      email_notifications_enabled: enabled,
    };
    await updateSettings(notificationFields);
  };

  const [isConnectingCalendar, setIsConnectingCalendar] = useState(false);

  useEffect(() => {
    if (!window.google?.accounts?.oauth2) {
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      document.body.appendChild(script);
    }
  }, []);

  const handleGoogleCalendarConnect = () => {
    if (!window.google?.accounts?.oauth2) {
      alert('Google authentication service is still loading. Please try again in a moment.');
      return;
    }

    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '424904983644-1r590marhlk27lgab1pja3ufcirtfkqb.apps.googleusercontent.com';
    
    setIsConnectingCalendar(true);

    try {
      const client = window.google.accounts.oauth2.initCodeClient({
        client_id: clientId,
        scope: 'https://www.googleapis.com/auth/calendar',
        ux_mode: 'popup',
        callback: async (response) => {
          if (response.error) {
            setIsConnectingCalendar(false);
            alert(`Google Calendar integration failed: ${response.error}`);
            return;
          }
          if (response.code) {
            try {
              const res = await apiRequest('/api/integrations/google/connect', {
                method: 'POST',
                body: JSON.stringify({ server_auth_code: response.code })
              });
              if (res.status === 'success' || res.message?.includes('connected')) {
                alert('Google Calendar connected successfully!');
                await fetchSettings();
                await fetchIntegrationStatus();
              } else {
                alert(res.message || 'Failed to link Google Calendar. Please try again.');
              }
            } catch (err) {
              alert(err.message || 'Failed to exchange authorization tokens.');
            } finally {
              setIsConnectingCalendar(false);
            }
          } else {
            setIsConnectingCalendar(false);
          }
        }
      });
      client.requestCode();
    } catch (err) {
      setIsConnectingCalendar(false);
      console.error(err);
      alert('Failed to initialize Google OAuth connection popup.');
    }
  };

  const handleGoogleCalendarDisconnect = async () => {
    if (!window.confirm('Are you sure you want to disconnect Google Calendar? This will disable schedule synchronization.')) {
      return;
    }

    setIsConnectingCalendar(true);
    try {
      const res = await apiRequest('/api/integrations/google', {
        method: 'DELETE'
      });
      if (res.status === 'success' || res.message?.includes('disconnected')) {
        alert('Google Calendar disconnected successfully.');
        await fetchSettings();
        await fetchIntegrationStatus();
      } else {
        alert(res.message || 'Failed to disconnect. Please try again.');
      }
    } catch (err) {
      alert(err.message || 'Failed to communicate with the server.');
    } finally {
      setIsConnectingCalendar(false);
    }
  };

  // 0=Monday … 6=Sunday — matches the backend/mobile/AI-server day-of-week convention.
  const getDayName = (dayNum) => {
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    return days[dayNum] || 'Monday';
  };

  const initials = user?.name ? user.name.charAt(0).toUpperCase() : 'A';

  return (
    <div className="settings-workspace animate-fade-in">
      <input id="avatar-file-input" type="file" accept="image/*" style={{ display: 'none' }} onChange={handleAvatarUpload} />
      
      {/* 1. Left Sidebar: Settings Categories Nav */}
      <div className="settings-left-pane">
        <div className="pane-header-container">
          <SettingsIcon size={20} className="pane-icon" />
          <h3 className="pane-title font-logo">Settings</h3>
        </div>

        {/* Profile Card Header */}
        <div className="settings-profile-summary">
          <div className="settings-avatar-circle" style={{ position: 'relative' }}>
            {avatarPreview ? (
              <img src={avatarPreview} alt="avatar" />
            ) : initials}
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
                  <div className="profile-identity-display">
                    <div className={`identity-avatar ${avatarPreview ? 'has-image' : ''}`}>
                      {avatarPreview ? <img src={avatarPreview} alt="Profile avatar" /> : initials}
                      <label className="avatar-edit-btn" title="Edit avatar" htmlFor="avatar-file-input" role="button" tabIndex={0} aria-label="Edit avatar" onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { const input = document.getElementById('avatar-file-input'); if (input) input.click(); } }}>
                        <Edit size={18} color="#fff" />
                      </label>
                    </div>
                    <div className="identity-info">
                      <h4>{user?.name || 'Areej'}</h4>
                      <p className="username">@{user?.username || 'areej_student'}</p>
                      <p className="email">{user?.email || 'student@domain.com'}</p>
                    </div>
                  </div>
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
                  <div className={`identity-avatar ${avatarPreview ? 'has-image' : ''}`}>
                    {avatarPreview ? <img src={avatarPreview} alt="Profile avatar" /> : initials}
                  </div>
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
                  <p className="row-desc">Synchronize study schedules and timelines automatically with Google Calendar.</p>
                </div>
                <div className="google-calendar-action-box">
                  {settings.google_calendar_sync_enabled ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span className="collab-status-badge accepted" style={{ fontSize: '12px', padding: '4px 8px', borderRadius: '4px', backgroundColor: 'rgba(34, 197, 94, 0.12)', color: '#22c55e', fontWeight: 'bold' }}>✓ Connected</span>
                      <button 
                        type="button"
                        className="btn btn-secondary disconnect-btn" 
                        onClick={handleGoogleCalendarDisconnect}
                        disabled={isConnectingCalendar}
                        style={{ padding: '6px 12px', fontSize: '12px', borderRadius: '6px', cursor: 'pointer' }}
                      >
                        Disconnect
                      </button>
                    </div>
                  ) : (
                    <button 
                      type="button"
                      className="btn btn-primary connect-btn" 
                      onClick={handleGoogleCalendarConnect}
                      disabled={isConnectingCalendar}
                      style={{ padding: '8px 16px', fontSize: '13px', borderRadius: '6px', cursor: 'pointer', background: 'linear-gradient(135deg, #4285F4 0%, #357AE8 100%)', color: 'white', border: 'none', fontWeight: '600' }}
                    >
                      {isConnectingCalendar ? 'Connecting...' : 'Connect Calendar'}
                    </button>
                  )}
                </div>
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
                    onChange={(e) => handleMasterNotificationToggle(e.target.checked)}
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
                <div className="settings-saas-row">
                  <div className="row-meta">
                    <span className="row-title">Enable Quiet Hours</span>
                    <p className="row-desc">Master switch — blocks below only take effect while this is on.</p>
                  </div>
                  <label className="toggle-switch-saas">
                    <input
                      type="checkbox"
                      checked={!!settings.quiet_hours_enabled}
                      onChange={(e) => handleQuietHoursEnabledToggle(e.target.checked)}
                    />
                    <span className="toggle-slider-saas" />
                  </label>
                </div>
                <div className="crud-header border-top">
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
                  <span>{editingScheduleId ? 'Edit Routine Template Slot' : 'Create Routine Template Slot'}</span>
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

                  {newScheduleForm.slots.map((slot, idx) => (
                    <div className="study-form-row" key={idx}>
                      <select
                        value={slot.day_of_week}
                        onChange={(e) => handleSlotFieldChange(idx, 'day_of_week', Number(e.target.value))}
                        className="study-form-select"
                      >
                        <option value="0">Monday</option>
                        <option value="1">Tuesday</option>
                        <option value="2">Wednesday</option>
                        <option value="3">Thursday</option>
                        <option value="4">Friday</option>
                        <option value="5">Saturday</option>
                        <option value="6">Sunday</option>
                      </select>

                      <input
                        type="time"
                        value={slot.start_time}
                        onChange={(e) => handleSlotFieldChange(idx, 'start_time', e.target.value)}
                        className="study-form-time"
                      />

                      <select
                        value={slot.duration_minutes}
                        onChange={(e) => handleSlotFieldChange(idx, 'duration_minutes', Number(e.target.value))}
                        className="study-form-select"
                      >
                        <option value="30">30 min</option>
                        <option value="60">60 min</option>
                        <option value="90">90 min</option>
                        <option value="120">120 min</option>
                      </select>

                      <button
                        type="button"
                        className="tile-delete-btn"
                        title="Remove this day/session"
                        onClick={() => handleRemoveSlotRow(idx)}
                        disabled={newScheduleForm.slots.length <= 1}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ))}

                  <div className="study-form-row">
                    <button type="button" className="btn btn-outlined" onClick={handleAddSlotRow}>
                      <Plus size={14} style={{ marginRight: '4px' }} /> Add another day/session
                    </button>
                  </div>

                  <div className="study-form-row">
                    <button className="crud-add-btn study-add-btn" onClick={handleCreateSchedule}>
                      <Plus size={16} /> {editingScheduleId ? 'Save Changes' : 'Create'}
                    </button>
                    {editingScheduleId && (
                      <button type="button" className="btn btn-outlined" onClick={handleCancelEditSchedule}>
                        Cancel
                      </button>
                    )}
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
                              <div className="sched-tile-actions">
                                <button className="tile-delete-btn" title="Edit schedule" onClick={() => handleEditScheduleClick(sched)}>
                                  <Edit size={14} />
                                </button>
                                <button className="tile-delete-btn" title="Delete schedule" onClick={() => handleRemoveSchedule(sched.id)}>
                                  <Trash2 size={14} />
                                </button>
                              </div>
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
