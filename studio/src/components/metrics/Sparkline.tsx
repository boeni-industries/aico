import React, { useState, useRef } from 'react';
import { Box, Portal } from '@mui/material';

interface SparklineProps {
  data: number[];
  color: string;
  width?: number;
  height?: number;
  strokeWidth?: number;
  showGradient?: boolean;
  invertY?: boolean;
  unit?: string;
  formatValue?: (value: number) => string;
  isNeutralMetric?: boolean;
  lowerIsBetter?: boolean;
}

export const Sparkline: React.FC<SparklineProps> = ({
  data,
  color,
  width = 80,
  height = 24,
  strokeWidth = 2,
  showGradient = true,
  invertY = false,
  unit = '',
  formatValue,
  isNeutralMetric = false,
  lowerIsBetter = false,
}) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  if (!data || data.length < 2) {
    return null;
  }

  // Calculate min/max for scaling
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1; // Avoid division by zero

  // Generate SVG path
  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * width;
    // Invert Y axis if invertY is true (for metrics where higher is better)
    const normalizedY = ((value - min) / range) * height;
    const y = invertY ? normalizedY : height - normalizedY;
    return { x, y };
  });

  // Create smooth curve path using quadratic bezier curves
  const pathData = points.reduce((path, point, index) => {
    if (index === 0) {
      return `M ${point.x},${point.y}`;
    }
    
    const prevPoint = points[index - 1];
    const midX = (prevPoint.x + point.x) / 2;
    
    return `${path} Q ${prevPoint.x},${prevPoint.y} ${midX},${(prevPoint.y + point.y) / 2} T ${point.x},${point.y}`;
  }, '');

  // Create area fill path
  const areaPath = `${pathData} L ${width},${height} L 0,${height} Z`;

  // Generate gradient ID
  const gradientId = `sparkline-gradient-${Math.random().toString(36).substr(2, 9)}`;

  // Handle mouse move to detect hover over data points
  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current || !containerRef.current) return;
    
    const svgRect = svgRef.current.getBoundingClientRect();
    const containerRect = containerRef.current.getBoundingClientRect();
    const x = e.clientX - svgRect.left;
    
    // Find closest data point
    const pointWidth = width / (data.length - 1);
    const index = Math.round(x / pointWidth);
    
    if (index >= 0 && index < data.length) {
      setHoveredIndex(index);
      // Store mouse position relative to container
      setMousePos({ 
        x: e.clientX - containerRect.left, 
        y: e.clientY - containerRect.top 
      });
    }
  };

  const handleMouseLeave = () => {
    setHoveredIndex(null);
  };

  // Format value for display
  const getFormattedValue = (value: number) => {
    if (formatValue) return formatValue(value);
    return `${value.toFixed(2)}${unit}`;
  };

  // Calculate time label (minutes ago)
  const getTimeLabel = (index: number) => {
    const minutesAgo = (data.length - 1 - index);
    if (minutesAgo === 0) return 'Now';
    if (minutesAgo === 1) return '1 min ago';
    return `${minutesAgo} min ago`;
  };

  // Calculate change magnitude and direction
  const firstValue = data[0];
  const lastValue = data[data.length - 1];
  const absoluteChange = lastValue - firstValue;
  const percentChange = firstValue !== 0 ? ((absoluteChange / firstValue) * 100) : 0;
  
  // Arrow direction always matches actual data movement
  const isIncreasing = absoluteChange > 0;
  const isDecreasing = absoluteChange < 0;
  
  // Determine if this change is good or bad based on metric type
  // lowerIsBetter: for metrics like response time, error rate (decrease = good)
  // !lowerIsBetter: for metrics like requests/sec, success rate (increase = good)
  const isGoodChange = lowerIsBetter ? isDecreasing : isIncreasing;
  const isBadChange = lowerIsBetter ? isIncreasing : isDecreasing;
  
  const isNoChange = Math.abs(percentChange) <= 5; // Less than 5% is considered no significant change
  const hasChange = true; // Always show indicator

  return (
    <>
      <Box
        ref={containerRef}
        sx={{
          display: 'inline-flex',
          flexDirection: 'column',
          alignItems: 'center',
          ml: 1,
          opacity: 0.9,
          transition: 'opacity 0.3s ease',
          position: 'relative',
          gap: 1,
          '&:hover': {
            opacity: 1,
          },
        }}
      >
        <svg
          ref={svgRef}
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          style={{
            overflow: 'visible',
            filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3))',
            cursor: 'crosshair',
          }}
        >
        <defs>
          {showGradient && (
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={color} stopOpacity="0.4" />
              <stop offset="100%" stopColor={color} stopOpacity="0.05" />
            </linearGradient>
          )}
        </defs>

        {/* Area fill with gradient */}
        {showGradient && (
          <path
            d={areaPath}
            fill={`url(#${gradientId})`}
            style={{
              transition: 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          />
        )}

        {/* Line stroke */}
        <path
          d={pathData}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            transition: 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        />

        {/* Endpoint dot */}
        <circle
          cx={points[points.length - 1].x}
          cy={points[points.length - 1].y}
          r={strokeWidth * 1.5}
          fill={color}
          style={{
            filter: `drop-shadow(0 0 4px ${color})`,
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        >
          <animate
            attributeName="r"
            values={`${strokeWidth * 1.5};${strokeWidth * 2};${strokeWidth * 1.5}`}
            dur="2s"
            repeatCount="indefinite"
          />
        </circle>

        {/* Hover indicator */}
        {hoveredIndex !== null && (
          <>
            {/* Vertical line at hover point */}
            <line
              x1={points[hoveredIndex].x}
              y1={0}
              x2={points[hoveredIndex].x}
              y2={height}
              stroke={color}
              strokeWidth={1}
              strokeDasharray="2,2"
              opacity={0.5}
            />
            {/* Hover dot */}
            <circle
              cx={points[hoveredIndex].x}
              cy={points[hoveredIndex].y}
              r={strokeWidth * 2}
              fill={color}
              stroke="rgba(255, 255, 255, 0.9)"
              strokeWidth={2}
              style={{
                filter: `drop-shadow(0 0 8px ${color})`,
              }}
            />
          </>
        )}
      </svg>

        {/* Change magnitude indicator - below sparkline, always visible */}
        {hasChange && (
          <Box
            sx={{
              px: 1,
              py: 0.5,
              borderRadius: '6px',
              bgcolor: isNeutralMetric
                ? 'rgba(59, 130, 246, 0.15)' // Blue for neutral metrics
                : isNoChange 
                  ? 'rgba(100, 116, 139, 0.15)' 
                  : isGoodChange 
                    ? 'rgba(16, 185, 129, 0.15)' 
                    : 'rgba(239, 68, 68, 0.15)',
              border: '1px solid',
              borderColor: isNeutralMetric
                ? 'rgba(59, 130, 246, 0.3)'
                : isNoChange
                  ? 'rgba(100, 116, 139, 0.3)'
                  : isGoodChange 
                    ? 'rgba(16, 185, 129, 0.3)' 
                    : 'rgba(239, 68, 68, 0.3)',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              animation: isNoChange ? 'none' : 'pulse 2s ease-in-out infinite',
              '@keyframes pulse': {
                '0%, 100%': { opacity: 1 },
                '50%': { opacity: 0.7 },
              },
            }}
          >
            <Box
              sx={{
                fontSize: '0.65rem',
                fontWeight: 700,
                color: isNeutralMetric
                  ? '#3B82F6' // Blue for neutral
                  : isNoChange 
                    ? '#64748B' 
                    : isGoodChange 
                      ? '#10B981' 
                      : '#EF4444',
                lineHeight: 1,
              }}
            >
              {isNoChange ? '→' : isIncreasing ? '↑' : '↓'}
            </Box>
            <Box
              sx={{
                fontSize: '0.6rem',
                fontWeight: 700,
                color: isNeutralMetric
                  ? '#3B82F6'
                  : isNoChange 
                    ? '#64748B' 
                    : isGoodChange 
                      ? '#10B981' 
                      : '#EF4444',
                letterSpacing: '0.02em',
                lineHeight: 1,
              }}
            >
              {Math.abs(percentChange).toFixed(0)}%
            </Box>
            <Box
              sx={{
                fontSize: '0.55rem',
                fontWeight: 500,
                color: isNeutralMetric
                  ? 'rgba(59, 130, 246, 0.8)'
                  : isNoChange 
                    ? 'rgba(100, 116, 139, 0.8)' 
                    : isGoodChange 
                      ? 'rgba(16, 185, 129, 0.8)' 
                      : 'rgba(239, 68, 68, 0.8)',
                letterSpacing: '0.01em',
                lineHeight: 1,
              }}
            >
              ({formatValue ? formatValue(Math.abs(absoluteChange)) : `${Math.abs(absoluteChange).toFixed(1)}${unit}`})
            </Box>
          </Box>
        )}
      </Box>

      {/* Beautiful tooltip - using Portal for maximum z-index */}
      {hoveredIndex !== null && containerRef.current && (
        <Portal>
          <Box
            sx={{
              position: 'fixed',
              left: containerRef.current.getBoundingClientRect().left + mousePos.x + 10,
              top: containerRef.current.getBoundingClientRect().top + mousePos.y - 50,
              zIndex: 999999,
              pointerEvents: 'none',
              animation: 'fadeIn 0.15s ease-out',
              '@keyframes fadeIn': {
                from: { opacity: 0, transform: 'translateY(4px)' },
                to: { opacity: 1, transform: 'translateY(0)' },
              },
            }}
          >
            <Box
              sx={{
                px: 1.5,
                py: 1,
                borderRadius: '8px',
                bgcolor: 'rgba(0, 0, 0, 0.9)',
                backdropFilter: 'blur(12px)',
                border: '1px solid',
                borderColor: `${color}40`,
                boxShadow: `0 4px 20px rgba(0, 0, 0, 0.4), 0 0 0 1px ${color}20`,
                display: 'flex',
                flexDirection: 'column',
                gap: 0.5,
                minWidth: 100,
              }}
            >
              <Box
                sx={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: color,
                  letterSpacing: '0.02em',
                }}
              >
                {getFormattedValue(data[hoveredIndex])}
              </Box>
              <Box
                sx={{
                  fontSize: '0.65rem',
                  color: 'rgba(255, 255, 255, 0.6)',
                  fontWeight: 500,
                }}
              >
                {getTimeLabel(hoveredIndex)}
              </Box>
            </Box>
          </Box>
        </Portal>
      )}
    </>
  );
};
