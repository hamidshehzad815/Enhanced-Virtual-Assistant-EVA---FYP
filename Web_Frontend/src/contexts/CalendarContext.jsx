import React, { createContext, useContext, useState, useEffect } from 'react';
import apiRequest from '../services/api';
import { useAuth } from './AuthContext';

const CalendarContext = createContext(null);

export const CalendarProvider = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [dashboardData, setDashboardData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDay, setSelectedDay] = useState(new Date());
  const [focusedDay, setFocusedDay] = useState(new Date());
  
  // Filters
  const [filterCategory, setFilterCategory] = useState(null);

  const fetchTasks = async (dateStr) => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      // Convert date to YYYY-MM-DD for filter
      const queryParams = [];
      if (dateStr) {
        queryParams.push(`date=${dateStr}`);
      }
      const queryString = queryParams.length ? `?${queryParams.join('&')}` : '';
      
      const response = await apiRequest(`/api/tasks${queryString}`);
      if (response.status === 'success' || response.data) {
        const list = response.data?.tasks || response.data || [];
        setTasks(list);
      }
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchDashboard = async () => {
    if (!isAuthenticated) return;
    try {
      const response = await apiRequest('/api/dashboard');
      if (response.status === 'success' || response.data) {
        setDashboardData(response.data);
      }
    } catch (err) {
      console.error('Failed to fetch dashboard:', err);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      // Fetch initial tasks for selected day
      const formattedDate = formatDateString(selectedDay);
      fetchTasks(formattedDate);
      fetchDashboard();
    }
  }, [isAuthenticated, selectedDay]);

  const toggleTask = async (taskId, currentStatus) => {
    const newStatus = currentStatus === 'complete' ? 'pending' : 'complete';
    try {
      // Optimistic update
      setTasks(prev => prev.map(t => t._id === taskId ? { ...t, status: newStatus } : t));
      
      const response = await apiRequest(`/api/tasks/${taskId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus })
      });
      
      if (response.status === 'success') {
        fetchDashboard(); // update progress stats
      }
    } catch (err) {
      console.error('Failed to toggle task:', err);
      // Revert
      const formattedDate = formatDateString(selectedDay);
      fetchTasks(formattedDate);
    }
  };

  const deleteTask = async (taskId) => {
    try {
      // Optimistic delete
      setTasks(prev => prev.filter(t => t._id !== taskId));
      
      const response = await apiRequest(`/api/tasks/${taskId}`, {
        method: 'DELETE'
      });
      
      if (response.status === 'success') {
        fetchDashboard();
      }
    } catch (err) {
      console.error('Failed to delete task:', err);
      const formattedDate = formatDateString(selectedDay);
      fetchTasks(formattedDate);
    }
  };

  const formatDateString = (date) => {
    const d = new Date(date);
    const month = '' + (d.getMonth() + 1);
    const day = '' + d.getDate();
    const year = d.getFullYear();

    return [year, month.padStart(2, '0'), day.padStart(2, '0')].join('-');
  };

  return (
    <CalendarContext.Provider value={{
      tasks,
      dashboardData,
      isLoading,
      selectedDay,
      focusedDay,
      filterCategory,
      setSelectedDay,
      setFocusedDay,
      setFilterCategory,
      toggleTask,
      deleteTask,
      fetchTasks,
      fetchDashboard,
      formatDateString
    }}>
      {children}
    </CalendarContext.Provider>
  );
};

export const useCalendar = () => useContext(CalendarContext);
