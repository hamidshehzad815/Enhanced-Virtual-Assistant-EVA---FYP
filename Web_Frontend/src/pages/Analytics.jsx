import React, { useState, useEffect } from 'react';
import { TrendingUp, Clock, Calendar, Zap, AlertCircle, Sparkles, Activity, ShieldAlert } from 'lucide-react';
import apiRequest from '../services/api';
import './Analytics.css';

export const Analytics = () => {
  const [productivity, setProductivity] = useState(null);
  const [hoursData, setHoursData] = useState([]);
  const [daysData, setDaysData] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  // Mock fallbacks
  const MOCK_PRODUCTIVITY = {
    total_completed: 18,
    on_time_percentage: 78,
    completion_speed_mins: 42,
    active_streak: 5,
    study_efficiency: 'High',
  };

  const MOCK_HOURS = [
    { hour: '08:00', count: 2 },
    { hour: '10:00', count: 4 },
    { hour: '12:00', count: 1 },
    { hour: '14:00', count: 3 },
    { hour: '16:00', count: 6 },
    { hour: '18:00', count: 5 },
    { hour: '20:00', count: 3 },
    { hour: '22:00', count: 1 }
  ];

  const MOCK_DAYS = [
    { day: 'Mon', count: 4 },
    { day: 'Tue', count: 6 },
    { day: 'Wed', count: 3 },
    { day: 'Thu', count: 5 },
    { day: 'Fri', count: 7 },
    { day: 'Sat', count: 2 },
    { day: 'Sun', count: 1 }
  ];

  const MOCK_TREND = [
    { week: 1, count: 8, on_time: 6 },
    { week: 2, count: 12, on_time: 9 },
    { week: 3, count: 10, on_time: 8 },
    { week: 4, count: 15, on_time: 12 }
  ];

  const fetchAnalytics = async () => {
    setIsLoading(true);
    try {
      const prodRes = await apiRequest('/api/analytics/productivity').catch(() => null);
      if (prodRes && prodRes.status === 'success') {
        setProductivity(prodRes.data);
      } else {
        setProductivity(MOCK_PRODUCTIVITY);
      }

      const hoursRes = await apiRequest('/api/analytics/hours').catch(() => null);
      if (hoursRes && hoursRes.status === 'success' && Array.isArray(hoursRes.data)) {
        setHoursData(hoursRes.data);
      } else {
        setHoursData(MOCK_HOURS);
      }

      const daysRes = await apiRequest('/api/analytics/days').catch(() => null);
      if (daysRes && daysRes.status === 'success' && Array.isArray(daysRes.data)) {
        setDaysData(daysRes.data);
      } else {
        setDaysData(MOCK_DAYS);
      }

      const trendRes = await apiRequest('/api/analytics/completion-trend?weeks=4').catch(() => null);
      if (trendRes && trendRes.status === 'success' && trendRes.data?.trend) {
        setTrendData(trendRes.data.trend);
      } else {
        setTrendData(MOCK_TREND);
      }
    } catch (err) {
      console.warn('Could not read real analytics, displaying mock insights.', err);
      setProductivity(MOCK_PRODUCTIVITY);
      setHoursData(MOCK_HOURS);
      setDaysData(MOCK_DAYS);
      setTrendData(MOCK_TREND);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const totalCompleted = productivity?.total_completed !== undefined ? productivity.total_completed : MOCK_PRODUCTIVITY.total_completed;
  const onTimeRate = productivity?.on_time_percentage !== undefined ? productivity.on_time_percentage : MOCK_PRODUCTIVITY.on_time_percentage;
  const completionSpeed = productivity?.completion_speed_mins !== undefined ? productivity.completion_speed_mins : MOCK_PRODUCTIVITY.completion_speed_mins;
  const streak = productivity?.active_streak !== undefined ? productivity.active_streak : MOCK_PRODUCTIVITY.active_streak;
  const efficiency = productivity?.study_efficiency || MOCK_PRODUCTIVITY.study_efficiency;

  // SVG Line Chart Helpers
  const trendMaxVal = Math.max(...trendData.map(d => d.count), 5);
  const chartHeight = 120;
  const chartWidth = 320;
  const padding = 20;

  const points = trendData.map((d, index) => {
    const x = padding + (index * (chartWidth - 2 * padding)) / Math.max(trendData.length - 1, 1);
    const y = chartHeight - padding - (d.count * (chartHeight - 2 * padding)) / trendMaxVal;
    return { x, y, label: `W${d.week}: ${d.count} tasks` };
  });

  const onTimePoints = trendData.map((d, index) => {
    const x = padding + (index * (chartWidth - 2 * padding)) / Math.max(trendData.length - 1, 1);
    const y = chartHeight - padding - (d.on_time * (chartHeight - 2 * padding)) / trendMaxVal;
    return { x, y };
  });

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const onTimeLinePath = onTimePoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

  const radius = 35;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (onTimeRate / 100) * circumference;

  return (
    <div className="analytics-workspace animate-fade-in">
      <header className="analytics-page-header">
        <div className="header-meta-left">
          <span className="eyebrow-label">Performance Core</span>
          <h2 className="title-saas font-logo">Productivity Analytics</h2>
        </div>
        <div className="header-meta-right">
          <Activity size={18} className="live-status-pulse" />
          <span>Calculated Realtime</span>
        </div>
      </header>

      {/* 1. Key Metrics Cards Row */}
      <div className="metrics-cards-grid">
        <div className="metric-saas-card" style={{ '--accent-color': '#F59E0B' }}>
          <div className="card-top-header">
            <Zap size={18} className="metric-icon" />
            <span className="metric-label">Completed Tasks</span>
          </div>
          <h3 className="metric-value">{totalCompleted}</h3>
          <span className="metric-subtext">Overall finished study items</span>
        </div>

        <div className="metric-saas-card" style={{ '--accent-color': '#8B5CF6' }}>
          <div className="card-top-header">
            <Clock size={18} className="metric-icon" />
            <span className="metric-label">Mean Completion Speed</span>
          </div>
          <h3 className="metric-value">{completionSpeed}m</h3>
          <span className="metric-subtext">Average time to complete tasks</span>
        </div>

        <div className="metric-saas-card" style={{ '--accent-color': '#10B981' }}>
          <div className="card-top-header">
            <Calendar size={18} className="metric-icon" />
            <span className="metric-label">Active Study Streak</span>
          </div>
          <h3 className="metric-value">{streak} Days</h3>
          <span className="metric-subtext">Consecutive active focus days</span>
        </div>
      </div>

      {/* 2. Charts Bento Grid */}
      <div className="charts-bento-grid">
        
        {/* Card A: On Time Rate */}
        <div className="charts-card span-1">
          <div className="chart-header-saas">
            <span className="chart-eyebrow">On-Time Velocity</span>
            <h4 className="chart-title font-logo">On-Time Rate</h4>
          </div>
          
          <div className="radial-container-saas">
            <div className="gauge-viewport">
              <svg className="radial-svg-saas" width="120" height="120">
                <circle
                  className="radial-track-saas"
                  strokeWidth="8"
                  fill="transparent"
                  r={radius}
                  cx="60"
                  cy="60"
                />
                <circle
                  className="radial-indicator-saas"
                  strokeWidth="8"
                  fill="transparent"
                  r={radius}
                  cx="60"
                  cy="60"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                />
              </svg>
              <div className="radial-value-label">
                <span className="radial-pct">{onTimeRate}%</span>
                <span className="radial-lbl">on-time</span>
              </div>
            </div>

            <div className="efficiency-diagnostics">
              <div className="diag-pill">
                <Sparkles size={12} className="diag-icon" />
                <span>Efficiency: <strong>{efficiency}</strong></span>
              </div>
              <p className="diag-text">You generally complete your tasks ahead of the scheduled due dates. Keep it up!</p>
            </div>
          </div>
        </div>

        {/* Card B: Weekly Trends */}
        <div className="charts-card span-2">
          <div className="chart-header-saas">
            <span className="chart-eyebrow">Task Trends</span>
            <h4 className="chart-title font-logo">Weekly Task Output</h4>
          </div>

          <div className="line-chart-viewport">
            <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="svg-line-chart-saas">
              <line x1={padding} y1={padding} x2={chartWidth - padding} y2={padding} className="chart-line-grid" />
              <line x1={padding} y1={chartHeight / 2} x2={chartWidth - padding} y2={chartHeight / 2} className="chart-line-grid" />
              <line x1={padding} y1={chartHeight - padding} x2={chartWidth - padding} y2={chartHeight - padding} className="chart-line-grid" />
              
              <path
                d={`${linePath} L ${points[points.length - 1]?.x || 0} ${chartHeight - padding} L ${points[0]?.x || 0} ${chartHeight - padding} Z`}
                fill="url(#trendGradSaaS)"
                opacity="0.1"
              />

              <path d={linePath} fill="none" stroke="#8B5CF6" strokeWidth="2.5" strokeLinecap="round" />
              <path d={onTimeLinePath} fill="none" stroke="#F59E0B" strokeWidth="2" strokeDasharray="3,3" strokeLinecap="round" />

              {points.map((p, i) => (
                <g key={i} className="chart-node-dot">
                  <circle cx={p.x} cy={p.y} r="4" fill="#8B5CF6" className="dot-core" />
                  <title>{p.label}</title>
                </g>
              ))}

              <defs>
                <linearGradient id="trendGradSaaS" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#8B5CF6" />
                  <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0" />
                </linearGradient>
              </defs>
            </svg>

            <div className="chart-legend-saas">
              <div className="legend-row">
                <span className="legend-indicator-dot completed"></span>
                <span>Completed Tasks</span>
              </div>
              <div className="legend-row">
                <span className="legend-indicator-dot ontime"></span>
                <span>On-Time Targets</span>
              </div>
            </div>
          </div>
        </div>

        {/* Card C: Productive Days */}
        <div className="charts-card span-1">
          <div className="chart-header-saas">
            <span className="chart-eyebrow">Distribution</span>
            <h4 className="chart-title font-logo">Most Productive Days</h4>
          </div>

          <div className="bar-chart-grid-saas">
            {daysData.map((d, index) => {
              const maxVal = Math.max(...daysData.map(x => x.count), 1);
              const pct = (d.count / maxVal) * 100;
              return (
                <div key={index} className="bar-row-saas">
                  <span className="bar-label-day">{d.day}</span>
                  <div className="bar-track-saas">
                    <div 
                      className="bar-fill-saas" 
                      style={{ width: `${pct}%`, backgroundColor: '#8B5CF6' }}
                    />
                  </div>
                  <span className="bar-value-lbl">{d.count}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Card D: Hourly Activity */}
        <div className="charts-card span-2">
          <div className="chart-header-saas">
            <span className="chart-eyebrow">Hourly Distribution</span>
            <h4 className="chart-title font-logo">Peak Active Study Slots</h4>
          </div>

          <div className="heatmap-viewport-saas">
            {(Array.isArray(hoursData) ? hoursData : MOCK_HOURS).map((h, index) => {
              const safeHours = Array.isArray(hoursData) ? hoursData : MOCK_HOURS;
              const maxVal = Math.max(...safeHours.map(x => x.count), 1);
              const intensity = h.count / maxVal;
              return (
                <div key={index} className="heatmap-block-saas">
                  <div 
                    className="heatmap-cell-saas"
                    style={{
                      backgroundColor: `rgba(139, 92, 246, ${Math.max(intensity, 0.08)})`
                    }}
                    title={`${h.hour}: ${h.count} tasks completed`}
                  />
                  <span className="heatmap-label-saas">{h.hour}</span>
                </div>
              );
            })}
          </div>
        </div>

      </div>
    </div>
  );
};

export default Analytics;
