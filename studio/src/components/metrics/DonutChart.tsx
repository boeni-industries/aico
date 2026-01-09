import React from 'react';
import { Box, Typography } from '@mui/material';

interface DonutChartProps {
  data: { label: string; value: number; color: string }[];
  size?: number;
  thickness?: number;
  showLegend?: boolean;
  centerLabel?: string;
  centerValue?: string | number;
}

export const DonutChart: React.FC<DonutChartProps> = ({
  data,
  size = 140,
  thickness = 24,
  showLegend = true,
  centerLabel,
  centerValue,
}) => {
  const total = data.reduce((sum, item) => sum + item.value, 0);
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;

  let currentOffset = 0;

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
      <Box
        sx={{
          position: 'relative',
          width: size,
          height: size,
          flexShrink: 0,
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
          {/* Data segments */}
          {data.map((item, index) => {
            const percentage = (item.value / total) * 100;
            const segmentLength = (percentage / 100) * circumference;
            const offset = currentOffset;
            currentOffset += segmentLength;

            return (
              <circle
                key={index}
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke={item.color}
                strokeWidth={thickness}
                strokeDasharray={`${segmentLength} ${circumference - segmentLength}`}
                strokeDashoffset={-offset}
                style={{
                  transition: 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
                }}
              />
            );
          })}
        </svg>
        {(centerLabel || centerValue) && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {centerValue && (
              <Typography
                variant="h4"
                sx={{
                  fontWeight: 700,
                  fontSize: '1.75rem',
                  color: 'text.primary',
                  lineHeight: 1,
                }}
              >
                {centerValue}
              </Typography>
            )}
            {centerLabel && (
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.65rem',
                  fontWeight: 600,
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                  color: 'text.secondary',
                  mt: 0.5,
                }}
              >
                {centerLabel}
              </Typography>
            )}
          </Box>
        )}
      </Box>
      {showLegend && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {data.map((item, index) => {
            const percentage = ((item.value / total) * 100).toFixed(1);
            return (
              <Box
                key={index}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                }}
              >
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: '3px',
                    bgcolor: item.color,
                    flexShrink: 0,
                  }}
                />
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontSize: '0.75rem',
                      color: 'text.primary',
                      fontWeight: 500,
                    }}
                  >
                    {item.label}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontSize: '0.75rem',
                      color: 'text.secondary',
                      fontWeight: 600,
                    }}
                  >
                    {item.value}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      fontSize: '0.7rem',
                      color: 'text.disabled',
                      minWidth: '42px',
                      textAlign: 'right',
                    }}
                  >
                    {percentage}%
                  </Typography>
                </Box>
              </Box>
            );
          })}
        </Box>
      )}
    </Box>
  );
};
