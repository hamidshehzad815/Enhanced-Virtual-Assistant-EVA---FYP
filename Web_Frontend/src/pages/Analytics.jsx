import React, { useState, useEffect } from 'react';
import { TrendingUp, Clock, Calendar, Zap, AlertCircle, Sparkles, Activity, ShieldAlert } from 'lucide-react';
import apiRequest from '../services/api';
import './Analytics.css';

export const Analytics = () => {
  const [analytics, setAnalytics] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await apiRequest('/api/analytics/dashboard?days=30');
      if (response?.status === 'success' && response.data) {
        setAnalytics(response.data);
      } else {
        setAnalytics(null);
        setError('No analytics data available.');
      }
    } catch (err) {
      console.error('Failed to fetch analytics dashboard:', err);
      setAnalytics(null);
      setError('Unable to load analytics data at this time.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const snapshot = analytics?.snapshot || {};
  const behavioral = analytics?.behavioral || {};
  const heatmap = analytics?.heatmap || {};
  const workPatterns = analytics?.work_patterns || {};
  const activity = analytics?.activity || {};

  const totalCompleted = snapshot.completed?.period ?? 0;
  const onTimeRate = Number(snapshot.on_time_rate ?? 0);
  const completionSpeed = behavioral.focus?.avg_minutes ?? 0;
  const streak = snapshot.current_streak ?? 0;
  const efficiency = snapshot.productivity_score?.rating || snapshot.productivity_score?.caption || 'Unknown';

  const activitySeries = Array.isArray(activity.series) ? activity.series : [];

  const trendData = activitySeries.length > 0
    ? (() => {
      const weeks = 4;
      const bucketSize = Math.ceil(activitySeries.length / weeks);
      return Array.from({ length: weeks }, (_, idx) => {
        const slice = activitySeries.slice(idx * bucketSize, (idx + 1) * bucketSize);
        const count = slice.reduce((sum, item) => sum + (item.count ?? 0), 0);
        const onTimeSum = slice.reduce((sum, item) => sum + (item.on_time ?? 0), 0);
        const onTimeRate = count > 0 ? Math.round((onTimeSum / count) * 100) : 0;
        return {
          week: idx + 1,
          count,
          on_time_rate: onTimeRate,
        };
      }).filter((item, index, array) => index < Math.max(array.length, 1));
    })()
    : [];

  const daysData = Array.isArray(behavioral.top_days) && behavioral.top_days.length > 0
    ? behavioral.top_days.map(d => ({ day: d.day || d.day_name || `Day ${d.day_num}`, count: d.log_count ?? 0 }))
    : [];

  const hoursData = Array.isArray(heatmap.cells) && heatmap.cells.length > 0
    ? heatmap.cells.reduce((groups, cell) => {
      const key = cell.hour_display || `${cell.hour}:00`;
      const existing = groups.find((item) => item.hour === key);
      if (existing) {
        existing.count += cell.count ?? 0;
      } else {
        groups.push({ hour: key, count: cell.count ?? 0 });
      }
      return groups;
    }, [])
    : [];

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
    const y = chartHeight - padding - (d.on_time_rate * (chartHeight - 2 * padding)) / 100;
    return { x, y };
  });

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const onTimeLinePath = onTimePoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

  const chartSize = 160;
  const strokeWidth = 12;
  const radius = (chartSize - strokeWidth) / 2;
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
              <svg className="radial-svg-saas" width="160" height="160" viewBox="0 0 160 160">
                <circle
                  className="radial-track-saas"
                  strokeWidth={strokeWidth}
                  fill="transparent"
                  r={radius}
                  cx="80"
                  cy="80"
                />
                <circle
                  className="radial-indicator-saas"
                  strokeWidth={strokeWidth}
                  fill="transparent"
                  r={radius}
                  cx="80"
                  cy="80"
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
            {Array.isArray(daysData) && daysData.length > 0 ? (
              daysData.map((d, index) => {
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
              })
            ) : (
              <div className="empty-state-panel">
                <AlertCircle size={18} />
                <span>No productivity day data available yet.</span>
              </div>
            )}
          </div>
        </div>

        {/* Card D: Hourly Activity */}
        <div className="charts-card span-2">
          <div className="chart-header-saas">
            <span className="chart-eyebrow">Hourly Distribution</span>
            <h4 className="chart-title font-logo">Peak Active Study Slots</h4>
          </div>

          <div className="heatmap-viewport-saas">
            {Array.isArray(hoursData) && hoursData.length > 0 ? (
              hoursData.map((h, index) => {
                const maxVal = Math.max(...hoursData.map(x => x.count), 1);
                const intensity = h.count / maxVal;
                return (
                  <div key={index} className="heatmap-block-saas">
                    <div 
                      className="heatmap-cell-saas"
                      style={{
                        backgroundColor: `rgba(139, 92, 246, ${Math.max(intensity, 0.08)})`
                      }}
                      title={`${h.hour_display || h.hour}: ${h.count} tasks completed`}
                    />
                    <span className="heatmap-label-saas">{h.hour_display || h.hour}</span>
                  </div>
                );
              })
            ) : (
              <div className="empty-state-panel">
                <AlertCircle size={18} />
                <span>No hourly activity data is available yet.</span>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default Analytics;
