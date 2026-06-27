import React, { createContext, useContext, useState, useEffect } from 'react';
import apiRequest from '../services/api';
import { useAuth } from './AuthContext';

const SettingsContext = createContext(null);

export const SettingsProvider = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const [settings, setSettings] = useState({
    notifications_enabled: true,
    push_notifications_enabled: true,
    email_notifications_enabled: false,
    quiet_hours: [],
    default_reminder_minutes: 30,
    default_topic_reminder_minutes: 15,
    default_task_priority: 'medium',
    default_task_duration: 120,
    preferred_learning_duration: 90,
    preferred_learning_time: 'afternoon',
    google_calendar_sync_enabled: false,
    allow_friend_requests: 'everyone',
    show_last_active: true,
    behavioral_analytics_enabled: true,
    analytics_min_tasks_threshold: 10,
    theme: 'light',
    language: 'en',
  });
  const [learningSchedules, setLearningSchedules] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchSettings = async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const response = await apiRequest('/api/settings');
      if (response.status === 'success' || response.data) {
        const s = response.data?.settings || response.data || response;
        setSettings(prev => ({ ...prev, ...s }));
        
        // Extract schedules if returned
        if (s.preferred_learning_schedules) {
          setLearningSchedules(s.preferred_learning_schedules);
        }
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchSchedules = async () => {
    if (!isAuthenticated) return;
    try {
      const response = await apiRequest('/api/settings/learning-schedules');
      if (response.status === 'success' || response.data) {
        const list = response.data?.preferred_learning_schedules || response.data || [];
        setLearningSchedules(list);
      }
    } catch (err) {
      console.error('Failed to fetch learning schedules:', err);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchSettings();
      fetchSchedules();
    }
  }, [isAuthenticated]);

  const updateSettings = async (newFields) => {
    try {
      // Optimistic update
      setSettings(prev => ({ ...prev, ...newFields }));
      
      const response = await apiRequest('/api/settings', {
        method: 'PATCH',
        body: JSON.stringify(newFields)
      });
      
      if (response.status === 'success') {
        const s = response.data?.settings || response.data || response;
        setSettings(prev => ({ ...prev, ...s }));
        
        // Handle theme change globally
        if (newFields.theme) {
          applyTheme(newFields.theme);
        }
        return { success: true };
      }
      return { success: false };
    } catch (err) {
      console.error('Failed to update settings:', err);
      // Rollback
      fetchSettings();
      return { success: false, message: err.message };
    }
  };

  const applyTheme = (themeValue) => {
    const root = window.document.documentElement;
    if (themeValue === 'dark') {
      root.classList.add('dark');
    } else if (themeValue === 'light') {
      root.classList.remove('dark');
    } else {
      // System
      const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (systemDark) {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    }
  };

  // Run on mount or theme update
  useEffect(() => {
    applyTheme(settings.theme);
  }, [settings.theme]);

  // CRUD for learning schedules
  const addSchedule = async (scheduleData) => {
    try {
      const response = await apiRequest('/api/settings/learning-schedules', {
        method: 'POST',
        body: JSON.stringify(scheduleData)
      });
      if (response.status === 'success' || response.statusCode === 201) {
        await fetchSchedules();
        return { success: true };
      }
      return { success: false };
    } catch (err) {
      console.error('Failed to add schedule:', err);
      return { success: false, message: err.message };
    }
  };

  const updateSchedule = async (scheduleId, scheduleData) => {
    try {
      const response = await apiRequest(`/api/settings/learning-schedules/${scheduleId}`, {
        method: 'PATCH',
        body: JSON.stringify(scheduleData)
      });
      if (response.status === 'success') {
        await fetchSchedules();
        return { success: true };
      }
      return { success: false };
    } catch (err) {
      console.error('Failed to update schedule:', err);
      return { success: false, message: err.message };
    }
  };

  const deleteSchedule = async (scheduleId) => {
    try {
      const response = await apiRequest(`/api/settings/learning-schedules/${scheduleId}`, {
        method: 'DELETE'
      });
      if (response.status === 'success') {
        await fetchSchedules();
        return { success: true };
      }
      return { success: false };
    } catch (err) {
      console.error('Failed to delete schedule:', err);
      return { success: false, message: err.message };
    }
  };

  return (
    <SettingsContext.Provider value={{
      settings,
      learningSchedules,
      isLoading,
      updateSettings,
      addSchedule,
      updateSchedule,
      deleteSchedule,
      fetchSettings,
      fetchSchedules
    }}>
      {children}
    </SettingsContext.Provider>
  );
};

export const useSettings = () => useContext(SettingsContext);
