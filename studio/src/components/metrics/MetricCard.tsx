import React from 'react';
import { Box, Typography, Tooltip } from '@mui/material';
import { TrendingUp, TrendingDown, Info } from 'lucide-react';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  trend?: number;
  status?: 'healthy' | 'warning' | 'critical';
  color?: string;
  tooltip?: string;
  size?: 'small' | 'medium' | 'large';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit = '',
  trend,
  status = 'healthy',
  color,
  tooltip,
  size = 'medium',
}) => {
  const statusColors = {
    healthy: '#10B981',
    warning: '#F59E0B',
    critical: '#EF4444',
  };

  const displayColor = color || statusColors[status];

  const sizeConfig = {
    small: { fontSize: '1.5rem', padding: 2 },
    medium: { fontSize: '2rem', padding: 2.5 },
    large: { fontSize: '2.5rem', padding: 3 },
  };

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        p: sizeConfig[size].padding,
        borderRadius: '16px',
        bgcolor: 'rgba(255, 255, 255, 0.02)',
        backdropFilter: 'blur(12px)',
        border: '1px solid',
        borderColor: 'rgba(255, 255, 255, 0.08)',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        '&:hover': {
          borderColor: `${displayColor}40`,
          transform: 'translateY(-2px)',
          boxShadow: `0 8px 32px ${displayColor}20`,
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1.5 }}>
        <Typography
          variant="caption"
          sx={{
            fontSize: '0.7rem',
            fontWeight: 600,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: 'text.secondary',
          }}
        >
          {label}
        </Typography>
        {tooltip && (
          <Tooltip title={tooltip} arrow>
            <Info size={12} style={{ color: 'rgba(255, 255, 255, 0.3)', cursor: 'help' }} />
          </Tooltip>
        )}
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
        <Typography
          variant="h4"
          sx={{
            fontSize: sizeConfig[size].fontSize,
            fontWeight: 700,
            color: displayColor,
            lineHeight: 1,
          }}
        >
          {value}
        </Typography>
        {unit && (
          <Typography
            variant="caption"
            sx={{
              fontSize: '0.85rem',
              fontWeight: 600,
              color: 'text.secondary',
            }}
          >
            {unit}
          </Typography>
        )}
      </Box>
      {trend !== undefined && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 0.5,
            mt: 1,
          }}
        >
          {trend > 0 ? (
            <TrendingUp size={14} style={{ color: '#10B981' }} />
          ) : trend < 0 ? (
            <TrendingDown size={14} style={{ color: '#EF4444' }} />
          ) : null}
          <Typography
            variant="caption"
            sx={{
              fontSize: '0.75rem',
              fontWeight: 600,
              color: trend > 0 ? '#10B981' : trend < 0 ? '#EF4444' : 'text.secondary',
            }}
          >
            {trend > 0 ? '+' : ''}
            {trend.toFixed(1)}%
          </Typography>
          <Typography
            variant="caption"
            sx={{
              fontSize: '0.7rem',
              color: 'text.disabled',
              ml: 0.5,
            }}
          >
            7d
          </Typography>
        </Box>
      )}
    </Box>
  );
};
