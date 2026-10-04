import React from 'react';
import { CheckCircle, EyeOff, AlertTriangle, HelpCircle, Circle } from 'lucide-react';
import { STATUS_MAPPING } from '../tokens';

export type StatusType = keyof typeof STATUS_MAPPING;

interface StatusBadgeProps {
  status: StatusType | string;
  size?: 'sm' | 'base';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'base' }) => {
  const normalizedStatus = (status in STATUS_MAPPING ? status : 'Unknown') as StatusType;
  const config = STATUS_MAPPING[normalizedStatus];

  const renderIcon = () => {
    const iconClass = size === 'sm' ? 'w-3 h-3 mr-space-1' : 'w-4 h-4 mr-space-2';
    switch (config.icon) {
      case 'check-circle':
        return <CheckCircle className={iconClass} aria-hidden="true" />;
      case 'eye-off':
        return <EyeOff className={iconClass} aria-hidden="true" />;
      case 'alert-triangle':
        return <AlertTriangle className={iconClass} aria-hidden="true" />;
      case 'dot':
        return <Circle className={`${iconClass} fill-current`} aria-hidden="true" />;
      case 'help-circle':
      default:
        return <HelpCircle className={iconClass} aria-hidden="true" />;
    }
  };

  const getStyleClasses = () => {
    switch (normalizedStatus) {
      case 'Attentive':
      case 'Normal':
      case 'Online':
        return 'text-accent-success bg-bg-success border-accent-success';
      case 'Distracted':
        return 'text-accent-primary bg-bg-info border-accent-primary';
      case 'Fatigued':
      case 'Offline':
      case 'Degraded':
        return 'text-accent-danger bg-bg-surface border-accent-danger';
      case 'Unknown':
      default:
        return 'text-text-secondary bg-bg-surface border-border-subtle';
    }
  };

  const sizeClasses = size === 'sm' 
    ? 'text-xs px-space-2 py-space-1' 
    : 'text-sm px-space-4 py-space-2';

  return (
    <span
      className={`inline-flex items-center font-medium border rounded-radius-pill transition-colors ${sizeClasses} ${getStyleClasses()}`}
      role="status"
      aria-label={`Status: ${config.text}`}
    >
      {renderIcon()}
      <span>{config.text}</span>
    </span>
  );
};
