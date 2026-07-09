import React, { createContext, useContext, useState, useEffect } from 'react';
import apiRequest from '../services/api';
import { useAuth } from './AuthContext';

const CalendarContext = createContext(null);

export const CalendarProvider = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const [allTasks, setAllTasks] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [dashboardData, setDashboardData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDay, setSelectedDay] = useState(new Date());
  const [focusedDay, setFocusedDay] = useState(new Date());
  
  // Filters
  const [filterCategory, setFilterCategory] = useState(null);

  const fetchTasks = async () => {
    if (!isAuthenticated) return;
    setIsLoading(true);
    try {
      const response = await apiRequest('/api/tasks/calendar');
      if (response.status === 'success' || response.data) {
        const list = response.data?.tasks || response.data || [];
        setAllTasks(list);
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
      fetchTasks();
      fetchDashboard();
    } else {
      setAllTasks([]);
      setTasks([]);
      setDashboardData(null);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    const formattedDate = formatDateString(selectedDay);
    const filtered = allTasks.filter(t => {
      if (!t.due_datetime) return false;
      const tDate = formatDateString(new Date(t.due_datetime));
      
      const dateMatch = tDate === formattedDate;
      const categoryMatch = !filterCategory || t.priority === filterCategory;
      
      return dateMatch && categoryMatch;
    });

    filtered.sort((a, b) => {
      if (a.status === 'complete' && b.status !== 'complete') return 1;
      if (b.status === 'complete' && a.status !== 'complete') return -1;
      const timeA = a.due_datetime ? new Date(a.due_datetime).getTime() : 0;
      const timeB = b.due_datetime ? new Date(b.due_datetime).getTime() : 0;
      return timeA - timeB;
    });

    setTasks(filtered);
  }, [allTasks, selectedDay, filterCategory]);

  const toggleTask = async (taskId, currentStatus) => {
    const newStatus = currentStatus === 'complete' ? 'pending' : 'complete';
    try {
      // Optimistic update
      setAllTasks(prev => prev.map(t => t._id === taskId ? { ...t, status: newStatus } : t));
      
      const response = await apiRequest(`/api/tasks/${taskId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus })
      });
      
      if (response.status === 'success') {
        fetchDashboard(); // update progress stats
      }
    } catch (err) {
      console.error('Failed to toggle task:', err);
      fetchTasks();
    }
  };

  const deleteTask = async (taskId) => {
    try {
      // Optimistic delete
      setAllTasks(prev => prev.filter(t => t._id !== taskId));
      
      const response = await apiRequest(`/api/tasks/${taskId}`, {
        method: 'DELETE'
      });
      
      if (response.status === 'success') {
        fetchDashboard();
      }
    } catch (err) {
      console.error('Failed to delete task:', err);
      fetchTasks();
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
      allTasks,
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
