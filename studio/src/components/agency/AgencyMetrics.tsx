import React from 'react';
import { Box, Paper, Typography, CircularProgress } from '@mui/material';
import { TrendingUp as TrendingUpIcon } from 'lucide-react';
import { AgencyMetrics as AgencyMetricsType } from '../../types/agency';

interface AgencyMetricsProps {
  metrics: AgencyMetricsType | null;
  loading?: boolean;
}

interface MetricCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  color?: string;
  icon?: React.ReactNode;
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, subtitle, color, icon }) => {
  return (
    <Paper
      sx={{
        p: 3,
        borderRadius: '28px',
        border: '1.5px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        backdropFilter: 'blur(20px)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.06)',
        transition: 'all 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: '0 12px 48px rgba(0,0,0,0.12)',
          borderColor: color ? `${color}40` : 'divider',
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1.5 }}>
        <Typography
          variant="caption"
          sx={{
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            fontWeight: 600,
            color: 'text.secondary',
            fontSize: '0.7rem',
          }}
        >
          {label}
        </Typography>
        {icon && (
          <Box 
            sx={{ 
              color: color || 'text.secondary',
              opacity: 0.6,
              '& svg': { fontSize: '1.25rem' }
            }}
          >
            {icon}
          </Box>
        )}
      </Box>
      <Typography
        variant="h3"
        sx={{
          fontWeight: 700,
          fontSize: '2.25rem',
          color: 'text.primary',
          mb: subtitle ? 0.5 : 0,
          textShadow: color ? `0 0 24px ${color}20` : 'none',
        }}
      >
        {value}
      </Typography>
      {subtitle && (
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
          {subtitle}
        </Typography>
      )}
    </Paper>
  );
};

const curiosityColors = {
  low: '#9CA3AF',
  medium: '#F59E0B',
  high: '#10B981',
};

export const AgencyMetrics: React.FC<AgencyMetricsProps> = ({ metrics, loading }) => {
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!metrics) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 8 }}>
        No metrics available
      </Typography>
    );
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: {
          xs: '1fr',
          sm: 'repeat(2, 1fr)',
          md: 'repeat(3, 1fr)',
        },
        gap: 3,
        mb: 4,
      }}
    >
      <MetricCard
        label="Active Goals"
        value={metrics.active_goals}
        subtitle="Currently being pursued"
        color="#B8A1EA"
      />
      <MetricCard
        label="Plans In-Flight"
        value={metrics.plans_in_flight}
        subtitle="Active execution plans"
        color="#3B82F6"
      />
      <MetricCard
        label="Proactive Messages"
        value={metrics.proactive_messages_24h}
        subtitle="Last 24 hours"
        color="#5EEAD4"
      />
      <MetricCard
        label="Curiosity Level"
        value={metrics.curiosity_level.toUpperCase()}
        subtitle="Current exploration intensity"
        color={curiosityColors[metrics.curiosity_level]}
      />
      <MetricCard
        label="Reflection Runs"
        value={metrics.reflection_runs_7d}
        subtitle="Last 7 days"
        color="#F59E0B"
        icon={<TrendingUpIcon fontSize="small" />}
      />
      <MetricCard
        label="Lessons Applied"
        value={metrics.lessons_applied}
        subtitle="Active learning insights"
        color="#10B981"
      />
    </Box>
  );
};
