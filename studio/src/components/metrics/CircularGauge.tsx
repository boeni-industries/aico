import React from 'react';
import { Box, Typography } from '@mui/material';

interface CircularGaugeProps {
  value: number;
  max?: number;
  size?: number;
  thickness?: number;
  color?: string;
  label?: string;
  unit?: string;
  showValue?: boolean;
}

export const CircularGauge: React.FC<CircularGaugeProps> = ({
  value,
  max = 100,
  size = 180,
  thickness = 16,
  color = '#F59E0B',
  label = 'HEALTH',
  unit = '',
  showValue = true,
}) => {
  const percentage = Math.min((value / max) * 100, 100);
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <Box
      sx={{
        position: 'relative',
        width: size,
        height: size,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255, 255, 255, 0.05)"
          strokeWidth={thickness}
        />
        {/* Progress circle with gradient */}
        <defs>
          <linearGradient id={`gauge-gradient-${label}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity={1} />
            <stop offset="100%" stopColor={color} stopOpacity={0.6} />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#gauge-gradient-${label})`}
          strokeWidth={thickness}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          style={{
            transition: 'stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        />
      </svg>
      {showValue && (
        <Box
          sx={{
            position: 'absolute',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Typography
            variant="h3"
            sx={{
              fontWeight: 700,
              fontSize: '2.5rem',
              color: color,
              lineHeight: 1,
            }}
          >
            {Math.round(value)}
          </Typography>
          <Typography
            variant="caption"
            sx={{
              fontSize: '0.7rem',
              fontWeight: 600,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: 'text.secondary',
              mt: 0.5,
            }}
          >
            {label}
          </Typography>
          {unit && (
            <Typography
              variant="caption"
              sx={{
                fontSize: '0.65rem',
                color: 'text.disabled',
              }}
            >
              {unit}
            </Typography>
          )}
        </Box>
      )}
    </Box>
  );
};
