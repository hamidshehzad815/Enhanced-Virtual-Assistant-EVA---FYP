import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar as CalendarIcon, Filter, Trash2, CheckCircle2, Circle, ChevronLeft, ChevronRight, MessageSquare, ListTodo } from 'lucide-react';
import { useCalendar } from '../contexts/CalendarContext';
import './Calendar.css';

export const Calendar = () => {
  const navigate = useNavigate();
  const {
    allTasks,
    tasks,
    selectedDay,
    focusedDay,
    setSelectedDay,
    setFocusedDay,
    toggleTask,
    deleteTask,
    formatDateString
  } = useCalendar();

  // Month navigation helpers
  const handlePrevMonth = () => {
    const prev = new Date(focusedDay.getFullYear(), focusedDay.getMonth() - 1, 1);
    setFocusedDay(prev);
  };

  const handleNextMonth = () => {
    const next = new Date(focusedDay.getFullYear(), focusedDay.getMonth() + 1, 1);
    setFocusedDay(next);
  };

  // Generate calendar days
  const getDaysInMonth = () => {
    const year = focusedDay.getFullYear();
    const month = focusedDay.getMonth();
    
    // First day of month
    const firstDay = new Date(year, month, 1);
    const startDayOfWeek = firstDay.getDay(); // 0 = Sunday, 1 = Monday...
    
    // Days in current month
    const totalDays = new Date(year, month + 1, 0).getDate();
    
    // Days in previous month (for padding)
    const prevTotalDays = new Date(year, month, 0).getDate();
    
    const days = [];
    
    // Pad previous month days
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      days.push({
        date: new Date(year, month - 1, prevTotalDays - i),
        isCurrentMonth: false
      });
    }
    
    // Current month days
    for (let i = 1; i <= totalDays; i++) {
      days.push({
        date: new Date(year, month, i),
        isCurrentMonth: true
      });
    }
    
    // Pad next month days to complete grid (multiples of 7)
    const remaining = 42 - days.length; // 6 rows of 7 = 42
    for (let i = 1; i <= remaining; i++) {
      days.push({
        date: new Date(year, month + 1, i),
        isCurrentMonth: false
      });
    }
    
    return days;
  };

  const isToday = (date) => {
    const today = new Date();
    return date.getDate() === today.getDate() &&
      date.getMonth() === today.getMonth() &&
      date.getFullYear() === today.getFullYear();
  };

  const isSelected = (date) => {
    return date.getDate() === selectedDay.getDate() &&
      date.getMonth() === selectedDay.getMonth() &&
      date.getFullYear() === selectedDay.getFullYear();
  };

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  
  const monthTitle = `${monthNames[focusedDay.getMonth()]} ${focusedDay.getFullYear()}`;
  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  const handleToggle = (taskId, currentStatus) => {
    toggleTask(taskId, currentStatus);
  };

  const handleDelete = (taskId) => {
    if (window.confirm('Are you sure you want to delete this task?')) {
      deleteTask(taskId);
    }
  };

  const activeTasks = tasks;

  return (
    <div className="calendar-workspace animate-fade-in">
      
      {/* Left Sidebar Column */}
      <div className="calendar-left-pane">
        <div className="pane-header-container">
          <CalendarIcon size={20} className="pane-icon" />
          <h3 className="pane-title font-logo">Schedules</h3>
        </div>

        {/* Ask EVA Shortcut */}
        <div className="ai-schedule-shortcut">
          <h4 className="shortcut-title font-logo">Need to Schedule?</h4>
          <p className="shortcut-desc">Ask EVA to schedule exams, study groups, or roadmaps using plain English.</p>
          <button className="shortcut-action-btn" onClick={() => navigate('/chat')}>
            <MessageSquare size={14} /> Open AI Playground
          </button>
        </div>
      </div>

      {/* Main Center Month Grid Panel */}
      <div className="calendar-center-pane">
        <div className="calendar-nav-bar">
          <div className="nav-info">
            <h2 className="nav-month-title font-logo">{monthTitle}</h2>
          </div>
          <div className="nav-buttons">
            <button className="cal-arrow-btn" onClick={handlePrevMonth}>
              <ChevronLeft size={16} />
            </button>
            <button className="cal-arrow-btn" onClick={handleNextMonth}>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        <div className="month-grid-card">
          <div className="weekday-header-row">
            {weekDays.map(day => (
              <div key={day} className="weekday-header-cell">{day}</div>
            ))}
          </div>

          <div className="month-days-grid-core">
            {getDaysInMonth().map((day, idx) => {
              const isTodayDay = isToday(day.date);
              const isSelectedDay = isSelected(day.date);
              const isCurr = day.isCurrentMonth;
              const formattedCellDate = formatDateString(day.date);
              const hasTasksOnDay = allTasks.some(t => {
                if (!t.due_datetime) return false;
                return formatDateString(new Date(t.due_datetime)) === formattedCellDate;
              });
              
              return (
                <div
                  key={idx}
                  className={`month-day-cell ${!isCurr ? 'other-month' : ''} ${isTodayDay ? 'today' : ''} ${isSelectedDay ? 'selected' : ''}`}
                  onClick={() => {
                    setSelectedDay(day.date);
                    setFocusedDay(day.date);
                  }}
                >
                  <span className="day-number-label">{day.date.getDate()}</span>
                  {/* Visual task indicator dot on cell */}
                  {isTodayDay && <span className="today-badge-dot"></span>}
                  {!isTodayDay && hasTasksOnDay && <span className="has-tasks-dot"></span>}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Right Sidebar Details Column */}
      <div className="calendar-right-pane">
        <div className="pane-header-container">
          <ListTodo size={18} className="pane-icon" />
          <h3 className="pane-title font-logo">
            {selectedDay.toLocaleDateString([], { month: 'short', day: 'numeric' })}
          </h3>
        </div>

        <div className="tasks-scroll-container">
          {activeTasks.length === 0 ? (
            <div className="empty-tasks-panel">
              <p>No tasks scheduled.</p>
              <span>Use the AI Assistant to schedule tasks on this day.</span>
            </div>
          ) : (
            <div className="tasks-grid-list">
              {activeTasks.map(task => {
                const isCompleted = task.status === 'complete';
                const taskDate = task.due_datetime ? new Date(task.due_datetime) : null;
                const now = new Date();
                const isPast = taskDate ? taskDate.getTime() < now.getTime() : false;
                const isOverdue = !isCompleted && isPast;
                const isUpcoming = !isCompleted && taskDate && taskDate.getTime() > now.getTime() + 24 * 60 * 60 * 1000;
                const isAvailable = !isCompleted && taskDate && taskDate.getTime() <= now.getTime() + 24 * 60 * 60 * 1000 && taskDate.getTime() >= now.getTime();

                return (
                  <div key={task._id} className={`task-saas-card ${isCompleted ? 'completed' : ''} ${isOverdue ? 'overdue' : ''} ${isUpcoming ? 'upcoming' : ''}`}>
                    <button className="task-saas-check" onClick={() => handleToggle(task._id, task.status)}>
                      {isCompleted ? (
                        <CheckCircle2 className="check-icon completed" size={18} />
                      ) : (
                        <Circle className="check-icon" size={18} />
                      )}
                    </button>

                    <div className="task-saas-content">
                      <h4 className="task-saas-title">{task.title}</h4>
                      <span className="task-saas-time">
                        {task.due_datetime ? new Date(task.due_datetime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'All day'}
                      </span>
                      <div className="task-saas-badges-row">
                        {isCompleted && <span className="task-state-pill completed">Completed</span>}
                        {isOverdue && <span className="task-state-pill overdue">Overdue</span>}
                        {isUpcoming && <span className="task-state-pill upcoming">Upcoming</span>}
                        {isAvailable && <span className="task-state-pill available">Available</span>}
                      </div>
                    </div>

                    <div className="task-saas-actions">
                      <span className={`priority-label ${task.priority}`}>
                        {task.priority}
                      </span>
                      <button className="task-saas-delete" onClick={() => handleDelete(task._id)}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

    </div>
  );
};

export default Calendar;
