import React from 'react';
import { Check, Clock, X, Trash2, AlertCircle } from 'lucide-react';
import './StatusIndicator.css';

/**
 * StatusIndicator
 * Displays the status of a collaborator or collaboration action
 * Statuses: pending, accepted, rejected, removed, expired
 */
export const StatusIndicator = ({ status, size = 'md', showLabel = true, label }) => {
  const getStatusConfig = (status) => {
    switch (status?.toLowerCase()) {
      case 'accepted':
      case 'accept':
        return {
          icon: Check,
          className: 'status-indicator-accepted',
          label: label || 'Accepted',
          color: '#10B981',
        };
      case 'pending':
        return {
          icon: Clock,
          className: 'status-indicator-pending',
          label: label || 'Pending',
          color: '#F59E0B',
        };
      case 'rejected':
      case 'reject':
        return {
          icon: X,
          className: 'status-indicator-rejected',
          label: label || 'Rejected',
          color: '#EF4444',
        };
      case 'removed':
        return {
          icon: Trash2,
          className: 'status-indicator-removed',
          label: label || 'Removed',
          color: '#6B7280',
        };
      case 'expired':
        return {
          icon: AlertCircle,
          className: 'status-indicator-expired',
          label: label || 'Expired',
          color: '#EF4444',
        };
      case 'cancelled':
        return {
          icon: AlertCircle,
          className: 'status-indicator-cancelled',
          label: label || 'Cancelled',
          color: '#6B7280',
        };
      default:
        return {
          icon: Clock,
          className: 'status-indicator-unknown',
          label: label || 'Unknown',
          color: '#9CA3AF',
        };
    }
  };

  const config = getStatusConfig(status);
  const IconComponent = config.icon;

  const iconSize = size === 'sm' ? 12 : size === 'lg' ? 20 : 16;

  return (
    <div className={`status-indicator ${config.className} size-${size}`}>
      <IconComponent size={iconSize} />
      {showLabel && <span className="status-label">{config.label}</span>}
    </div>
  );
};

export default StatusIndicator;
