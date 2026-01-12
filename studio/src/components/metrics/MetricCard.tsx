import React, { useRef, useEffect, useState } from 'react';
import { Box, Typography } from '@mui/material';
import { TrendingUp, TrendingDown, Info } from 'lucide-react';
import { Sparkline } from './Sparkline';
import { StyledTooltip } from '../common/StyledTooltip';
import { formatMetricValue } from '../../utils/formatNumber';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  trend?: number;
  status?: 'healthy' | 'warning' | 'critical';
  color?: string;
  tooltip?: string;
  size?: 'small' | 'medium' | 'large';
  sparklineData?: number[];
  invertSparkline?: boolean;
  isNeutralMetric?: boolean;
  lowerIsBetter?: boolean;
  avg_1h?: number | null;
  avg_24h?: number | null;
  avg_7d?: number | null;
  onClick?: () => void;
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
  sparklineData,
  invertSparkline = false,
  isNeutralMetric = false,
  lowerIsBetter = false,
  avg_1h,
  avg_24h,
  avg_7d,
  onClick,
}) => {
  const sparklineContainerRef = useRef<HTMLDivElement>(null);
  const [sparklineWidth, setSparklineWidth] = useState(200);

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

  // Measure sparkline container width
  useEffect(() => {
    if (!sparklineContainerRef.current || !sparklineData) return;

    const updateWidth = () => {
      if (sparklineContainerRef.current) {
        const width = sparklineContainerRef.current.offsetWidth;
        if (width > 0) {
          setSparklineWidth(width);
        }
      }
    };

    updateWidth();

    const resizeObserver = new ResizeObserver(updateWidth);
    resizeObserver.observe(sparklineContainerRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [sparklineData]);

  return (
    <Box
      onClick={onClick}
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
        cursor: onClick ? 'pointer' : 'default',
        '&:hover': {
          borderColor: `${displayColor}40`,
          transform: onClick ? 'translateY(-2px)' : 'none',
          boxShadow: `0 8px 32px ${displayColor}20`,
        },
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
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
            <StyledTooltip title={tooltip} arrow>
              <Info size={12} style={{ color: 'rgba(255, 255, 255, 0.3)', cursor: 'help' }} />
            </StyledTooltip>
          )}
        </Box>
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: sparklineData ? 0.5 : 0, width: '100%' }}>
        <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1, flexShrink: 0 }}>
          <Typography
            variant="h4"
            sx={{
              fontSize: sizeConfig[size].fontSize,
              fontWeight: 700,
              color: displayColor,
              lineHeight: 1,
            }}
          >
            {formatMetricValue(value, unit)}
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
          {trend !== undefined && trend !== 0 && !isNeutralMetric && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.3,
                ml: 0.5,
              }}
            >
              {/* For lowerIsBetter metrics: negative trend (down) is good (green), positive trend (up) is bad (red) */}
              {/* For higherIsBetter metrics: positive trend (up) is good (green), negative trend (down) is bad (red) */}
              {lowerIsBetter ? (
                trend < 0 ? (
                  <TrendingDown size={16} style={{ color: '#10B981' }} />
                ) : (
                  <TrendingUp size={16} style={{ color: '#EF4444' }} />
                )
              ) : (
                trend > 0 ? (
                  <TrendingUp size={16} style={{ color: '#10B981' }} />
                ) : (
                  <TrendingDown size={16} style={{ color: '#EF4444' }} />
                )
              )}
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  color: lowerIsBetter 
                    ? (trend < 0 ? '#10B981' : '#EF4444')
                    : (trend > 0 ? '#10B981' : '#EF4444'),
                }}
              >
                {Math.abs(trend).toFixed(1)}%
              </Typography>
            </Box>
          )}
        </Box>
        {sparklineData && sparklineData.length > 1 && (
          <Box 
            ref={sparklineContainerRef}
            sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', minWidth: 0, mr: -1 }}
          >
            <Sparkline
              data={sparklineData}
              color={displayColor}
              width={sparklineWidth}
              height={size === 'small' ? 20 : size === 'large' ? 40 : 24}
              strokeWidth={size === 'small' ? 1.5 : size === 'large' ? 2.5 : 2}
              showGradient={true}
              invertY={invertSparkline}
              unit={unit}
              isNeutralMetric={isNeutralMetric}
              lowerIsBetter={lowerIsBetter}
            />
          </Box>
        )}
      </Box>
      {(avg_1h !== undefined || avg_24h !== undefined || avg_7d !== undefined) && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 2,
            mt: 2,
            mb: 0.5,
            px: 1,
            flexWrap: 'nowrap',
          }}
        >
          {avg_1h !== undefined && (
            <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.4, whiteSpace: 'nowrap' }}>
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.6rem',
                  fontWeight: 600,
                  color: 'rgba(255, 255, 255, 0.5)',
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                }}
              >
                1h
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  color: avg_1h !== null ? 'rgba(255, 255, 255, 0.9)' : 'rgba(255, 255, 255, 0.3)',
                }}
              >
                {avg_1h !== null ? `${avg_1h.toFixed(1)}${unit}` : 'no data'}
              </Typography>
            </Box>
          )}
          {avg_24h !== undefined && (
            <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.4, whiteSpace: 'nowrap' }}>
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.6rem',
                  fontWeight: 600,
                  color: 'rgba(255, 255, 255, 0.5)',
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                }}
              >
                24h
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  color: avg_24h !== null ? 'rgba(255, 255, 255, 0.9)' : 'rgba(255, 255, 255, 0.3)',
                }}
              >
                {avg_24h !== null ? `${avg_24h.toFixed(1)}${unit}` : 'no data'}
              </Typography>
            </Box>
          )}
          {avg_7d !== undefined && (
            <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.4, whiteSpace: 'nowrap' }}>
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.6rem',
                  fontWeight: 600,
                  color: 'rgba(255, 255, 255, 0.5)',
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase',
                }}
              >
                7d
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  fontSize: '0.7rem',
                  fontWeight: 600,
                  color: avg_7d !== null ? 'rgba(255, 255, 255, 0.9)' : 'rgba(255, 255, 255, 0.3)',
                }}
              >
                {avg_7d !== null ? `${avg_7d.toFixed(1)}${unit}` : 'no data'}
              </Typography>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
};
