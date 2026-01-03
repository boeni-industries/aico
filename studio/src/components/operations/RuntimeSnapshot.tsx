import React from 'react';
import { Box, Typography, Paper, Chip } from '@mui/material';
import {
  CheckCircle as HealthyIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Cloud as CloudIcon,
  Memory as ModelIcon,
  Schedule as ScheduleIcon,
  Message as BusIcon,
  Dashboard as StudioIcon,
} from '@mui/icons-material';

interface ServiceHealth {
  status: 'healthy' | 'degraded' | 'critical';
  uptime: string;
  latency?: number;
  jobs?: number;
  throughput?: number;
  users?: number;
}

interface RuntimeSnapshotProps {
  servicesHealth: {
    gateway: ServiceHealth;
    modelservice: ServiceHealth;
    scheduler: ServiceHealth;
    bus: ServiceHealth;
    studio: ServiceHealth;
  };
}

const statusConfig = {
  healthy: { 
    icon: HealthyIcon, 
    color: '#10B981', 
    bg: 'rgba(16, 185, 129, 0.12)', 
    border: 'rgba(16, 185, 129, 0.3)',
    label: 'HEALTHY'
  },
  degraded: { 
    icon: WarningIcon, 
    color: '#F59E0B', 
    bg: 'rgba(245, 158, 11, 0.12)', 
    border: 'rgba(245, 158, 11, 0.3)',
    label: 'DEGRADED'
  },
  critical: { 
    icon: ErrorIcon, 
    color: '#EF4444', 
    bg: 'rgba(239, 68, 68, 0.12)', 
    border: 'rgba(239, 68, 68, 0.3)',
    label: 'CRITICAL'
  },
};

const serviceConfig = {
  gateway: { icon: CloudIcon, label: 'Gateway', metric: 'latency', unit: 'ms' },
  modelservice: { icon: ModelIcon, label: 'Model Service', metric: 'latency', unit: 'ms' },
  scheduler: { icon: ScheduleIcon, label: 'Scheduler', metric: 'jobs', unit: 'jobs' },
  bus: { icon: BusIcon, label: 'Message Bus', metric: 'throughput', unit: 'msg/s' },
  studio: { icon: StudioIcon, label: 'Studio', metric: 'users', unit: 'active' },
};

export const RuntimeSnapshot: React.FC<RuntimeSnapshotProps> = ({ servicesHealth }) => {
  const overallStatus = Object.values(servicesHealth).some(s => s.status === 'critical') 
    ? 'critical' 
    : Object.values(servicesHealth).some(s => s.status === 'degraded')
    ? 'degraded'
    : 'healthy';

  return (
    <Paper
      sx={{
        p: 3,
        borderRadius: '20px',
        bgcolor: 'rgba(255, 255, 255, 0.02)',
        backdropFilter: 'blur(12px)',
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            textTransform: 'uppercase',
            fontSize: '0.75rem',
            letterSpacing: '0.1em',
            color: 'text.secondary',
          }}
        >
          Runtime Snapshot
        </Typography>
        <Chip
          icon={React.createElement(statusConfig[overallStatus].icon, { sx: { fontSize: 16 } })}
          label={statusConfig[overallStatus].label}
          size="small"
          sx={{
            bgcolor: statusConfig[overallStatus].bg,
            color: statusConfig[overallStatus].color,
            border: '1px solid',
            borderColor: statusConfig[overallStatus].border,
            fontWeight: 700,
            fontSize: '0.7rem',
            height: 24,
          }}
        />
      </Box>

      <Box sx={{ display: 'flex', gap: 2, overflowX: 'auto', pb: 1 }}>
        {Object.entries(servicesHealth).map(([key, health]) => {
          const config = serviceConfig[key as keyof typeof serviceConfig];
          const status = statusConfig[health.status];
          const StatusIcon = status.icon;
          const ServiceIcon = config.icon;
          const metricValue = health[config.metric as keyof ServiceHealth];

          return (
            <Paper
              key={key}
              sx={{
                p: 2.5,
                minWidth: 180,
                borderRadius: '16px',
                border: '1.5px solid',
                borderColor: status.border,
                bgcolor: status.bg,
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  boxShadow: `0 8px 24px ${status.color}20`,
                  borderColor: status.color,
                },
              }}
            >
              {/* Service Icon & Status */}
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Box
                  sx={{
                    width: 32,
                    height: 32,
                    borderRadius: '8px',
                    bgcolor: status.color + '20',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <ServiceIcon sx={{ fontSize: 18, color: status.color }} />
                </Box>
                <StatusIcon sx={{ fontSize: 18, color: status.color }} />
              </Box>

              {/* Service Label */}
              <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.8rem', mb: 1 }}>
                {config.label}
              </Typography>

              {/* Metric */}
              <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.5, mb: 1 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, color: status.color, fontSize: '1.1rem' }}>
                  {metricValue}
                </Typography>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem' }}>
                  {config.unit}
                </Typography>
              </Box>

              {/* Uptime */}
              <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem' }}>
                Uptime: {health.uptime}
              </Typography>
            </Paper>
          );
        })}
      </Box>
    </Paper>
  );
};
