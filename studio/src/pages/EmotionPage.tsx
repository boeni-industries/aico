import React from 'react';
import { Box, Paper, Typography, CircularProgress, Alert, Tooltip, Slider, ToggleButton, ToggleButtonGroup, Chip, useTheme, IconButton, Menu, MenuItem, ListItemIcon, ListItemText } from '@mui/material';
import { Download as DownloadIcon, MoreVertical as MoreVertIcon } from 'lucide-react';
import { fetchEmotionHistory, EmotionHistoryItemDto } from '../api/emotion';

function sortHistory(history: EmotionHistoryItemDto[]): EmotionHistoryItemDto[] {
  return [...history].sort((a, b) => (a.timestamp < b.timestamp ? -1 : a.timestamp > b.timestamp ? 1 : 0));
}

function formatTooltipTimestamp(timestamp: string): { date: string; time: string } {
  try {
    // Handle ISO 8601 format with timezone
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) {
      console.warn('Invalid timestamp:', timestamp);
      // Try regex fallback for ISO format
      const match = timestamp.match(/(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/);
      if (match) {
        const [, year, month, day, hours, minutes, seconds] = match;
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return {
          date: `${months[parseInt(month) - 1]} ${parseInt(day)}, ${year}`,
          time: `${hours}:${minutes}:${seconds}`
        };
      }
      return { date: timestamp, time: '' };
    }
    
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const month = months[date.getMonth()];
    const day = date.getDate();
    const year = date.getFullYear();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    
    return {
      date: `${month} ${day}, ${year}`,
      time: `${hours}:${minutes}:${seconds}`
    };
  } catch (e) {
    console.error('Error formatting timestamp:', e);
    return { date: timestamp, time: '' };
  }
}

function colorForEmotion(_feeling: string, valence: number, arousal: number): string {
  // High-contrast, accessible color mapping for emotion quadrants
  // Designed for visibility in low light and for vision-impaired users
  // Each quadrant has distinct hue with strong saturation and appropriate lightness
  
  let hue: number;
  let baseSat: number;
  let baseLight: number;
  
  if (valence >= 0 && arousal >= 0.5) {
    // Energetic pleasant: Bright orange/amber (high energy, positive)
    hue = 35;
    baseSat = 85;
    baseLight = 55;
  } else if (valence >= 0 && arousal < 0.5) {
    // Calm pleasant: Vibrant green/emerald (low energy, positive)
    hue = 145;
    baseSat = 75;
    baseLight = 45;
  } else if (valence < 0 && arousal >= 0.5) {
    // Energetic unpleasant: Bold red/crimson (high energy, negative)
    hue = 0;
    baseSat = 85;
    baseLight = 50;
  } else {
    // Calm unpleasant: Deep blue/sapphire (low energy, negative)
    hue = 220;
    baseSat = 75;
    baseLight = 50;
  }

  // Modulate saturation and lightness based on arousal for additional distinction
  // Higher arousal = more saturated and slightly lighter
  const sat = baseSat + arousal * 10; // Add up to 10% saturation
  const light = baseLight + arousal * 8; // Add up to 8% lightness
  
  return `hsl(${hue}, ${sat}%, ${light}%)`;
}

const EmotionStrip: React.FC<{ history: EmotionHistoryItemDto[]; windowHours: number }> = ({ history, windowHours }) => {
  const samples = sortHistory(history);
  if (samples.length === 0) return null;

  return (
    <Paper
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
      }}
    >
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
        Emotion strip (last {windowHours <= 24 ? `${windowHours}h` : `${Math.round(windowHours / 24)}d`})
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Each segment represents one recorded emotional state. Color encodes valence and arousal; opacity reflects
        intensity.
      </Typography>
      <Box
        sx={{
          mt: 1,
          height: 56,
          borderRadius: 999,
          overflow: 'hidden',
          display: 'grid',
          gridTemplateColumns: `repeat(${samples.length}, 1fr)`,
        }}
      >
        {samples.map((item) => {
          const color = colorForEmotion(item.feeling, item.valence, item.arousal);
          const opacity = 0.3 + item.intensity * 0.7;
          const { date, time } = formatTooltipTimestamp(item.timestamp);
          
          const tooltipContent = (
            <Box sx={{ py: 1.25, px: 1.75 }}>
              {/* Emotion name with color indicator */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.25 }}>
                <Box
                  sx={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    bgcolor: color,
                    flexShrink: 0,
                  }}
                />
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: 600,
                    fontSize: '0.875rem',
                    textTransform: 'capitalize',
                    letterSpacing: '0.01em',
                  }}
                >
                  {item.feeling}
                </Typography>
              </Box>
              
              {/* Timestamp */}
              <Box sx={{ mb: 1.25, pl: 0 }}>
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    fontSize: '0.7rem',
                    color: 'text.secondary',
                    lineHeight: 1.3,
                  }}
                >
                  {date || 'Invalid date'}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    fontSize: '0.75rem',
                    fontWeight: 500,
                    fontFamily: 'monospace',
                    letterSpacing: '0.03em',
                    mt: 0.25,
                  }}
                >
                  {time || 'Invalid time'}
                </Typography>
              </Box>
              
              {/* Metrics with refined layout */}
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: 1.25,
                  pt: 1.25,
                  borderTop: 1,
                  borderColor: 'divider',
                }}
              >
                <Box sx={{ textAlign: 'center' }}>
                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      fontSize: '0.625rem',
                      color: 'text.secondary',
                      textTransform: 'uppercase',
                      letterSpacing: '0.06em',
                      mb: 0.5,
                      fontWeight: 500,
                    }}
                  >
                    Valence
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      fontSize: '0.875rem',
                      fontFamily: 'monospace',
                    }}
                  >
                    {item.valence.toFixed(2)}
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      fontSize: '0.625rem',
                      color: 'text.secondary',
                      textTransform: 'uppercase',
                      letterSpacing: '0.06em',
                      mb: 0.5,
                      fontWeight: 500,
                    }}
                  >
                    Arousal
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      fontSize: '0.875rem',
                      fontFamily: 'monospace',
                    }}
                  >
                    {item.arousal.toFixed(2)}
                  </Typography>
                </Box>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography
                    variant="caption"
                    sx={{
                      display: 'block',
                      fontSize: '0.625rem',
                      color: 'text.secondary',
                      textTransform: 'uppercase',
                      letterSpacing: '0.06em',
                      mb: 0.5,
                      fontWeight: 500,
                    }}
                  >
                    Intensity
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: 600,
                      fontSize: '0.875rem',
                      fontFamily: 'monospace',
                    }}
                  >
                    {item.intensity.toFixed(2)}
                  </Typography>
                </Box>
              </Box>
            </Box>
          );
          
          return (
            <Tooltip
              key={item.timestamp}
              title={tooltipContent}
              arrow
              componentsProps={{
                tooltip: {
                  sx: {
                    bgcolor: 'background.paper',
                    color: 'text.primary',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.12), 0 2px 8px rgba(0,0,0,0.08)',
                    border: 1,
                    borderColor: 'divider',
                    borderRadius: 1,
                    p: 0,
                    maxWidth: 300,
                    backdropFilter: 'blur(8px)',
                    '& .MuiTooltip-arrow': {
                      color: 'background.paper',
                      '&::before': {
                        border: 1,
                        borderColor: 'divider',
                      },
                    },
                  },
                },
              }}
              enterDelay={200}
              enterNextDelay={100}
              leaveDelay={0}
            >
              <Box
                sx={{
                  bgcolor: color,
                  opacity,
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    opacity: Math.min(opacity + 0.15, 1),
                    transform: 'scaleY(1.1)',
                  },
                }}
              />
            </Tooltip>
          );
        })}
      </Box>
    </Paper>
  );
};

const EmotionCircumplex: React.FC<{ history: EmotionHistoryItemDto[] }> = ({ history }) => {
  const theme = useTheme();
  const textColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.9)' : 'rgba(0,0,0,0.8)';
  const textColorSecondary = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.78)' : 'rgba(0,0,0,0.65)';
  const lineColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.16)' : 'rgba(0,0,0,0.12)';
  const circleStroke = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)';
  const samples = sortHistory(history);

  const radius = 120;
  const baseSize = radius * 2 + 16;
  const padding = 80;

  const points = samples.map((item, index) => {
    // valence [-1,1] -> x [-r,r], arousal [0,1] -> y [r,-r]
    const x = (item.valence / 1) * radius;
    const y = radius - item.arousal * radius * 2;
    const color = colorForEmotion(item.feeling, item.valence, item.arousal);
    const opacity = 0.4 + item.intensity * 0.6;
    return { x, y, color, opacity, item, key: `${item.timestamp}-${index}` };
  });

  return (
    <Paper
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
        borderRadius: 1,
      }}
    >
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
        Valence–arousal circumplex
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Recent states in valence–arousal space.
      </Typography>
      <Box sx={{ mt: 1, display: 'flex', justifyContent: 'center' }}>
        <svg
          width={baseSize + padding * 2}
          height={baseSize + padding * 2}
          viewBox={`${-radius - padding} ${-radius - padding} ${baseSize + padding * 2} ${baseSize + padding * 2}`}
        >
          <defs>
            <clipPath id="emotionCircClip">
              <circle cx={0} cy={0} r={radius} />
            </clipPath>
          </defs>
          {/* Quadrant backgrounds for quick reading, clipped to the circle */}
          <g clipPath="url(#emotionCircClip)">
            <rect
              x={0}
              y={-radius}
              width={radius}
              height={radius}
              fill="rgba(0, 200, 140, 0.10)" // energetic & pleasant
            />
            <rect
              x={-radius}
              y={-radius}
              width={radius}
              height={radius}
              fill="rgba(220, 70, 90, 0.10)" // energetic & unpleasant
            />
            <rect
              x={0}
              y={0}
              width={radius}
              height={radius}
              fill="rgba(80, 170, 255, 0.08)" // calm & pleasant
            />
            <rect
              x={-radius}
              y={0}
              width={radius}
              height={radius}
              fill="rgba(80, 90, 150, 0.10)" // calm & unpleasant
            />
          </g>
          <circle
            cx={0}
            cy={0}
            r={radius}
            fill="none"
            stroke={circleStroke}
            strokeWidth={1}
          />
          <line x1={-radius} y1={0} x2={radius} y2={0} stroke={lineColor} strokeWidth={1} />
          <line x1={0} y1={-radius} x2={0} y2={radius} stroke={lineColor} strokeWidth={1} />
          {/* Axis labels - cardinal points outside circle */}
          <text x={0} y={-radius - 20} fill={textColor} fontSize={11} textAnchor="middle">
            high arousal
          </text>
          <text x={0} y={radius + 32} fill={textColor} fontSize={11} textAnchor="middle">
            low arousal
          </text>
          <text x={radius + 45} y={5} fill={textColor} fontSize={11} textAnchor="middle">
            pleasant
          </text>
          <text x={-radius - 45} y={5} fill={textColor} fontSize={11} textAnchor="middle">
            unpleasant
          </text>
          {/* Quadrant descriptions - diagonal positions outside circle */}
          <text
            x={radius * 0.707 + 8}
            y={-radius * 0.707 - 24}
            fill={textColorSecondary}
            fontSize={10}
            textAnchor="middle"
          >
            energetic
          </text>
          <text
            x={radius * 0.707 + 8}
            y={-radius * 0.707 - 12}
            fill={textColorSecondary}
            fontSize={10}
            textAnchor="middle"
          >
            pleasant
          </text>
          <text
            x={-radius * 0.707 - 8}
            y={-radius * 0.707 - 24}
            fill={textColorSecondary}
            fontSize={10}
            textAnchor="middle"
          >
            energetic
          </text>
          <text
            x={-radius * 0.707 - 8}
            y={-radius * 0.707 - 12}
            fill={textColorSecondary}
            fontSize={10}
            textAnchor="middle"
          >
            unpleasant
          </text>
          <text
            x={radius * 0.707 + 8}
            y={radius * 0.707 + 18}
            fill={textColorSecondary}
            fontSize={10}
            textAnchor="middle"
          >
            calm
          </text>
          <text
            x={radius * 0.707 + 8}
            y={radius * 0.707 + 30}
            fill={textColorSecondary}
            fontSize={10}
            textAnchor="middle"
          >
            pleasant
          </text>
          <text
            x={-radius * 0.707 - 8}
            y={radius * 0.707 + 18}
            fill={textColorSecondary}
            fontSize={10}
            textAnchor="middle"
          >
            calm
          </text>
          <text
            x={-radius * 0.707 - 8}
            y={radius * 0.707 + 30}
            fill={textColorSecondary}
            fontSize={10}
            textAnchor="middle"
          >
            unpleasant
          </text>
          {points.map((p) => (
            <Tooltip
              key={p.key}
              title={`${p.item.feeling} • v=${p.item.valence.toFixed(2)}, a=${p.item.arousal.toFixed(2)}, i=${p.item.intensity.toFixed(
                2,
              )}`}
              arrow
            >
              <circle cx={p.x} cy={p.y} r={5} fill={p.color} fillOpacity={p.opacity} />
            </Tooltip>
          ))}
        </svg>
      </Box>
    </Paper>
  );
};

const EmotionTimeSeries: React.FC<{ history: EmotionHistoryItemDto[] }> = ({ history }) => {
  const theme = useTheme();
  const [selectedMetric, setSelectedMetric] = React.useState<'all' | 'valence' | 'arousal' | 'intensity'>('all');
  const [hoveredIndex, setHoveredIndex] = React.useState<number | null>(null);
  const samples = sortHistory(history);
  
  const axisTextColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.6)' : 'rgba(0,0,0,0.5)';
  const gridColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)';
  const gridColorLight = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)';
  const axisColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.2)';
  const indicatorColor = theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.2)';
  const markerStroke = theme.palette.mode === 'dark' ? 'white' : 'rgba(0,0,0,0.8)';
  
  if (samples.length === 0) return null;

  const width = 800;
  const height = 200;
  const padding = { top: 20, right: 20, bottom: 40, left: 50 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Format timestamp for x-axis (short format)
  const formatTimeShort = (timestamp: string) => {
    try {
      // Parse ISO timestamp from backend
      const date = new Date(timestamp);
      if (!date || isNaN(date.getTime())) {
        console.warn('Invalid timestamp for short format:', timestamp);
        return '';
      }
      const hours = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      return `${hours}:${minutes}`;
    } catch (e) {
      console.error('Error formatting timestamp short:', timestamp, e);
      return '';
    }
  };

  // Format timestamp for tooltip (readable format)
  const formatTimeFull = (timestamp: string) => {
    try {
      // Parse ISO timestamp from backend (e.g., "2025-12-27T00:28:00.123456+00:00")
      const date = new Date(timestamp);
      if (!date || isNaN(date.getTime())) {
        console.warn('Invalid timestamp for full format:', timestamp);
        // Fallback: try to extract readable parts from string
        const match = timestamp.match(/(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
        if (match) {
          const [, year, month, day, hours, minutes] = match;
          const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
          return `${months[parseInt(month) - 1]} ${parseInt(day)}, ${hours}:${minutes}`;
        }
        return timestamp.substring(0, 19).replace('T', ' ');
      }
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const month = months[date.getMonth()];
      const day = date.getDate();
      const hours = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      return `${month} ${day}, ${hours}:${minutes}`;
    } catch (e) {
      console.error('Error formatting timestamp full:', timestamp, e);
      return timestamp.substring(0, 19).replace('T', ' ');
    }
  };

  // Get time labels for x-axis
  const getTimeLabels = () => {
    if (samples.length === 0) return [];
    if (samples.length === 1) {
      return [{ index: 0, label: formatTimeShort(samples[0].timestamp) }];
    }
    
    const labels = [];
    const numLabels = Math.min(6, samples.length);
    
    // Calculate step to distribute labels evenly
    if (numLabels === samples.length) {
      // Show all if we have few samples
      for (let i = 0; i < samples.length; i++) {
        labels.push({ index: i, label: formatTimeShort(samples[i].timestamp) });
      }
    } else {
      // Distribute evenly across the range
      for (let i = 0; i < numLabels; i++) {
        const index = Math.round((i / (numLabels - 1)) * (samples.length - 1));
        labels.push({ index, label: formatTimeShort(samples[index].timestamp) });
      }
    }
    
    return labels;
  };

  const timeLabels = getTimeLabels();

  const xScale = (index: number) => (index / Math.max(samples.length - 1, 1)) * chartWidth;
  const yScale = (value: number) => chartHeight - (value + 1) * (chartHeight / 2); // Map [-1, 1] to chart height

  const createPath = (values: number[]) => {
    if (values.length === 0) return '';
    return values
      .map((val, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)},${yScale(val)}`)
      .join(' ');
  };

  const valenceData = samples.map(s => s.valence);
  const arousalData = samples.map(s => s.arousal * 2 - 1); // Map [0, 1] to [-1, 1] for consistent scale
  const intensityData = samples.map(s => s.intensity * 2 - 1); // Map [0, 1] to [-1, 1]

  return (
    <Paper
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
        borderRadius: 1,
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          Emotion dimensions over time
        </Typography>
        <ToggleButtonGroup
          value={selectedMetric}
          exclusive
          onChange={(_, value) => value && setSelectedMetric(value)}
          size="small"
        >
          <ToggleButton value="all">All</ToggleButton>
          <ToggleButton value="valence">Valence</ToggleButton>
          <ToggleButton value="arousal">Arousal</ToggleButton>
          <ToggleButton value="intensity">Intensity</ToggleButton>
        </ToggleButtonGroup>
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Time-series showing how emotional dimensions evolve across the selected window.
      </Typography>
      
      {/* Fixed height tooltip container - NEVER changes height */}
      <Box sx={{ height: 60, display: 'flex', alignItems: 'flex-end', justifyContent: 'center', mb: 1 }}>
        {hoveredIndex !== null && (
          <Box 
            sx={{ 
              p: 1.5, 
              bgcolor: 'background.paper',
              borderRadius: 1, 
              fontSize: '0.875rem',
              border: '1px solid',
              borderColor: 'divider',
              boxShadow: 2,
            }}
          >
            <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
              {formatTimeFull(samples[hoveredIndex].timestamp)} • {samples[hoveredIndex].feeling}
            </Typography>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Typography variant="caption" color="hsl(200, 70%, 55%)">
                Valence: {samples[hoveredIndex].valence.toFixed(3)}
              </Typography>
              <Typography variant="caption" color="hsl(30, 80%, 60%)">
                Arousal: {samples[hoveredIndex].arousal.toFixed(3)}
              </Typography>
              <Typography variant="caption" color="hsl(280, 60%, 65%)">
                Intensity: {samples[hoveredIndex].intensity.toFixed(3)}
              </Typography>
            </Box>
          </Box>
        )}
      </Box>
      
      <Box sx={{ display: 'flex', justifyContent: 'center', overflowX: 'auto' }}>
        <svg width={width} height={height} style={{ minWidth: width }}>
          <g transform={`translate(${padding.left},${padding.top})`}>
            {/* Grid lines */}
            <line x1={0} y1={chartHeight / 2} x2={chartWidth} y2={chartHeight / 2} stroke={gridColor} strokeWidth={1} />
            <line x1={0} y1={0} x2={chartWidth} y2={0} stroke={gridColorLight} strokeWidth={1} />
            <line x1={0} y1={chartHeight} x2={chartWidth} y2={chartHeight} stroke={gridColorLight} strokeWidth={1} />
            
            {/* Y-axis labels */}
            <text x={-10} y={0} fill={axisTextColor} fontSize={10} textAnchor="end" dominantBaseline="middle">
              1.0
            </text>
            <text x={-10} y={chartHeight / 2} fill={axisTextColor} fontSize={10} textAnchor="end" dominantBaseline="middle">
              0.0
            </text>
            <text x={-10} y={chartHeight} fill={axisTextColor} fontSize={10} textAnchor="end" dominantBaseline="middle">
              -1.0
            </text>
            
            {/* Valence line */}
            {(selectedMetric === 'all' || selectedMetric === 'valence') && (
              <path
                d={createPath(valenceData)}
                fill="none"
                stroke="hsl(200, 70%, 55%)"
                strokeWidth={2}
                opacity={selectedMetric === 'valence' ? 1 : 0.7}
              />
            )}
            
            {/* Arousal line */}
            {(selectedMetric === 'all' || selectedMetric === 'arousal') && (
              <path
                d={createPath(arousalData)}
                fill="none"
                stroke="hsl(30, 80%, 60%)"
                strokeWidth={2}
                opacity={selectedMetric === 'arousal' ? 1 : 0.7}
              />
            )}
            
            {/* Intensity line */}
            {(selectedMetric === 'all' || selectedMetric === 'intensity') && (
              <path
                d={createPath(intensityData)}
                fill="none"
                stroke="hsl(280, 60%, 65%)"
                strokeWidth={2}
                opacity={selectedMetric === 'intensity' ? 1 : 0.7}
              />
            )}
            
            {/* Hover points */}
            {samples.map((sample, i) => (
              <g key={i}>
                {/* Larger invisible hit area for easier hovering */}
                <rect
                  x={xScale(i) - 15}
                  y={0}
                  width={30}
                  height={chartHeight}
                  fill="transparent"
                  style={{ cursor: 'pointer' }}
                  onMouseEnter={() => setHoveredIndex(i)}
                  onMouseLeave={() => setHoveredIndex(null)}
                />
                {hoveredIndex === i && (
                  <>
                    {/* Vertical indicator line */}
                    <line
                      x1={xScale(i)}
                      y1={0}
                      x2={xScale(i)}
                      y2={chartHeight}
                      stroke={indicatorColor}
                      strokeWidth={1}
                      strokeDasharray="4 2"
                    />
                    {/* Data point markers */}
                    {(selectedMetric === 'all' || selectedMetric === 'valence') && (
                      <circle cx={xScale(i)} cy={yScale(valenceData[i])} r={4} fill="hsl(200, 70%, 55%)" stroke={markerStroke} strokeWidth={1.5} />
                    )}
                    {(selectedMetric === 'all' || selectedMetric === 'arousal') && (
                      <circle cx={xScale(i)} cy={yScale(arousalData[i])} r={4} fill="hsl(30, 80%, 60%)" stroke={markerStroke} strokeWidth={1.5} />
                    )}
                    {(selectedMetric === 'all' || selectedMetric === 'intensity') && (
                      <circle cx={xScale(i)} cy={yScale(intensityData[i])} r={4} fill="hsl(280, 60%, 65%)" stroke={markerStroke} strokeWidth={1.5} />
                    )}
                  </>
                )}
              </g>
            ))}
            
            {/* Axes */}
            <line x1={0} y1={0} x2={0} y2={chartHeight} stroke={axisColor} strokeWidth={1} />
            <line x1={0} y1={chartHeight} x2={chartWidth} y2={chartHeight} stroke={axisColor} strokeWidth={1} />
            
            {/* X-axis time labels */}
            {timeLabels.length > 0 && timeLabels.map(({ index, label }) => {
              if (!label || label.trim() === '') return null;
              return (
                <text
                  key={index}
                  x={xScale(index)}
                  y={chartHeight + 25}
                  fill={axisTextColor}
                  fontSize={10}
                  textAnchor="middle"
                >
                  {label}
                </text>
              );
            })}
          </g>
        </svg>
      </Box>
      
      {/* Legend */}
      <Box sx={{ display: 'flex', gap: 3, justifyContent: 'center', mt: 1 }}>
        {(selectedMetric === 'all' || selectedMetric === 'valence') && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 20, height: 2, bgcolor: 'hsl(200, 70%, 55%)' }} />
            <Typography variant="caption" color="text.secondary">
              Valence (pleasant ↔ unpleasant)
            </Typography>
          </Box>
        )}
        {(selectedMetric === 'all' || selectedMetric === 'arousal') && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 20, height: 2, bgcolor: 'hsl(30, 80%, 60%)' }} />
            <Typography variant="caption" color="text.secondary">
              Arousal (activation level)
            </Typography>
          </Box>
        )}
        {(selectedMetric === 'all' || selectedMetric === 'intensity') && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ width: 20, height: 2, bgcolor: 'hsl(280, 60%, 65%)' }} />
            <Typography variant="caption" color="text.secondary">
              Intensity (emotional strength)
            </Typography>
          </Box>
        )}
      </Box>
      
    </Paper>
  );
};

const EmotionStatistics: React.FC<{ history: EmotionHistoryItemDto[] }> = ({ history }) => {
  if (history.length === 0) return null;

  const calcStats = (values: number[]) => {
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length;
    const stdDev = Math.sqrt(variance);
    const min = Math.min(...values);
    const max = Math.max(...values);
    
    // Calculate volatility (average absolute change between consecutive values)
    const changes = values.slice(1).map((v, i) => Math.abs(v - values[i]));
    const volatility = changes.length > 0 ? changes.reduce((a, b) => a + b, 0) / changes.length : 0;
    
    return { mean, stdDev, min, max, volatility };
  };

  const valenceStats = calcStats(history.map(h => h.valence));
  const arousalStats = calcStats(history.map(h => h.arousal));
  const intensityStats = calcStats(history.map(h => h.intensity));

  const StatRow: React.FC<{ label: string; value: string; color?: string }> = ({ label, value, color }) => (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
      <Typography variant="caption" color="text.secondary" sx={{ minWidth: 60 }}>
        {label}
      </Typography>
      <Typography variant="caption" sx={{ fontFamily: 'monospace', fontWeight: 600, color: color || 'text.primary' }}>
        {value}
      </Typography>
    </Box>
  );

  return (
    <Paper
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
        borderRadius: 1,
      }}
    >
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
        Statistical summary
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Descriptive statistics for emotional dimensions over the selected window.
      </Typography>
      
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 3, mt: 1 }}>
        {/* Valence column */}
        <Box sx={{ p: 1.5, bgcolor: 'rgba(200, 180, 255, 0.05)', borderRadius: 1, border: '1px solid rgba(200, 180, 255, 0.1)' }}>
          <Typography variant="caption" sx={{ fontWeight: 600, color: 'hsl(200, 70%, 55%)', display: 'block', mb: 1.5, fontSize: '0.8rem' }}>
            Valence
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
            <StatRow label="Mean" value={valenceStats.mean.toFixed(3)} />
            <StatRow label="Std Dev" value={valenceStats.stdDev.toFixed(3)} />
            <StatRow label="Range" value={`${valenceStats.min.toFixed(2)} → ${valenceStats.max.toFixed(2)}`} />
            <StatRow label="Volatility" value={valenceStats.volatility.toFixed(3)} />
          </Box>
        </Box>
        
        {/* Arousal column */}
        <Box sx={{ p: 1.5, bgcolor: 'rgba(255, 180, 120, 0.05)', borderRadius: 1, border: '1px solid rgba(255, 180, 120, 0.1)' }}>
          <Typography variant="caption" sx={{ fontWeight: 600, color: 'hsl(30, 80%, 60%)', display: 'block', mb: 1.5, fontSize: '0.8rem' }}>
            Arousal
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
            <StatRow label="Mean" value={arousalStats.mean.toFixed(3)} />
            <StatRow label="Std Dev" value={arousalStats.stdDev.toFixed(3)} />
            <StatRow label="Range" value={`${arousalStats.min.toFixed(2)} → ${arousalStats.max.toFixed(2)}`} />
            <StatRow label="Volatility" value={arousalStats.volatility.toFixed(3)} />
          </Box>
        </Box>
        
        {/* Intensity column */}
        <Box sx={{ p: 1.5, bgcolor: 'rgba(220, 160, 255, 0.05)', borderRadius: 1, border: '1px solid rgba(220, 160, 255, 0.1)' }}>
          <Typography variant="caption" sx={{ fontWeight: 600, color: 'hsl(280, 60%, 65%)', display: 'block', mb: 1.5, fontSize: '0.8rem' }}>
            Intensity
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.75 }}>
            <StatRow label="Mean" value={intensityStats.mean.toFixed(3)} />
            <StatRow label="Std Dev" value={intensityStats.stdDev.toFixed(3)} />
            <StatRow label="Range" value={`${intensityStats.min.toFixed(2)} → ${intensityStats.max.toFixed(2)}`} />
            <StatRow label="Volatility" value={intensityStats.volatility.toFixed(3)} />
          </Box>
        </Box>
      </Box>
    </Paper>
  );
};

interface Episode {
  type: 'stress' | 'regulation' | 'stability';
  startIndex: number;
  endIndex: number;
  duration: number;
  avgValence: number;
  avgArousal: number;
}

const EmotionEpisodes: React.FC<{ history: EmotionHistoryItemDto[] }> = ({ history }) => {
  const samples = sortHistory(history);
  
  if (samples.length === 0) return null;

  // Detect episodes based on emotional patterns
  const detectEpisodes = (): Episode[] => {
    const episodes: Episode[] = [];
    let currentEpisode: Episode | null = null;

    for (let i = 0; i < samples.length; i++) {
      const sample = samples[i];
      const isStress = sample.valence < -0.3 && sample.arousal > 0.6;
      const isRegulation = i > 0 && samples[i - 1].arousal > 0.7 && sample.arousal < samples[i - 1].arousal - 0.2;
      const isStable = Math.abs(sample.valence) < 0.3 && sample.arousal < 0.4;

      const episodeType = isStress ? 'stress' : isRegulation ? 'regulation' : isStable ? 'stability' : null;

      if (episodeType) {
        if (currentEpisode && currentEpisode.type === episodeType) {
          // Extend current episode
          currentEpisode.endIndex = i;
          currentEpisode.duration++;
        } else {
          // Start new episode
          if (currentEpisode && currentEpisode.duration >= 2) {
            episodes.push(currentEpisode);
          }
          currentEpisode = {
            type: episodeType,
            startIndex: i,
            endIndex: i,
            duration: 1,
            avgValence: sample.valence,
            avgArousal: sample.arousal,
          };
        }
      } else {
        // End current episode if it's long enough
        if (currentEpisode && currentEpisode.duration >= 2) {
          episodes.push(currentEpisode);
        }
        currentEpisode = null;
      }
    }

    // Add final episode if exists
    if (currentEpisode && currentEpisode.duration >= 2) {
      episodes.push(currentEpisode);
    }

    // Calculate average values for each episode
    return episodes.map(ep => {
      const episodeSamples = samples.slice(ep.startIndex, ep.endIndex + 1);
      return {
        ...ep,
        avgValence: episodeSamples.reduce((sum, s) => sum + s.valence, 0) / episodeSamples.length,
        avgArousal: episodeSamples.reduce((sum, s) => sum + s.arousal, 0) / episodeSamples.length,
      };
    });
  };

  const episodes = detectEpisodes();

  const getEpisodeColor = (type: Episode['type']) => {
    switch (type) {
      case 'stress': return 'error';
      case 'regulation': return 'success';
      case 'stability': return 'info';
    }
  };

  const getEpisodeLabel = (type: Episode['type']) => {
    switch (type) {
      case 'stress': return 'Stress Episode';
      case 'regulation': return 'Regulation Event';
      case 'stability': return 'Stable Period';
    }
  };

  return (
    <Paper
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
        borderRadius: 1,
      }}
    >
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
        Detected episodes
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Automatically detected emotional patterns: stress episodes, regulation events, and stable periods.
      </Typography>
      
      {episodes.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic', mt: 1 }}>
          No significant episodes detected in the current window.
        </Typography>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1 }}>
          {episodes.map((episode, i) => (
            <Box
              key={i}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                p: 1,
                bgcolor: 'rgba(255,255,255,0.03)',
                borderRadius: 1,
              }}
            >
              <Chip
                label={getEpisodeLabel(episode.type)}
                color={getEpisodeColor(episode.type)}
                size="small"
                sx={{ minWidth: 140 }}
              />
              <Box sx={{ flex: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  {samples[episode.startIndex].timestamp} → {samples[episode.endIndex].timestamp}
                </Typography>
                <Typography variant="caption" display="block" color="text.secondary">
                  Duration: {episode.duration} states • Avg valence: {episode.avgValence.toFixed(2)} • Avg arousal: {episode.avgArousal.toFixed(2)}
                </Typography>
              </Box>
            </Box>
          ))}
        </Box>
      )}
    </Paper>
  );
};

// Export utility functions
const exportEmotionCSV = (history: EmotionHistoryItemDto[]) => {
  const headers = ['timestamp', 'feeling', 'valence', 'arousal', 'intensity'];
  const rows = history.map(h => [
    h.timestamp,
    h.feeling,
    h.valence.toString(),
    h.arousal.toString(),
    h.intensity.toString(),
  ]);
  
  const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `emotion-history-${new Date().toISOString()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
};

const exportEmotionJSON = (history: EmotionHistoryItemDto[]) => {
  const json = JSON.stringify(history, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `emotion-history-${new Date().toISOString()}.json`;
  a.click();
  URL.revokeObjectURL(url);
};

// Page actions menu component - exported for use in StudioLayout
export const EmotionPageActions: React.FC<{ history: EmotionHistoryItemDto[] }> = ({ history }) => {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleExportCSV = () => {
    exportEmotionCSV(history);
    handleClose();
  };

  const handleExportJSON = () => {
    exportEmotionJSON(history);
    handleClose();
  };

  return (
    <>
      <IconButton
        size="small"
        onClick={handleClick}
        aria-label="page actions"
        sx={{ color: 'text.secondary' }}
      >
        <MoreVertIcon fontSize="small" />
      </IconButton>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <MenuItem onClick={handleExportCSV}>
          <ListItemIcon>
            <DownloadIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Export as CSV</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleExportJSON}>
          <ListItemIcon>
            <DownloadIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Export as JSON</ListItemText>
        </MenuItem>
      </Menu>
    </>
  );
};

const EmotionLabelDistribution: React.FC<{ history: EmotionHistoryItemDto[] }> = ({ history }) => {
  const counts = history.reduce<Record<string, number>>((acc, item) => {
    acc[item.feeling] = (acc[item.feeling] || 0) + 1;
    return acc;
  }, {});

  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const total = history.length || 1;

  return (
    <Paper
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 1.5,
        borderRadius: 1,
      }}
    >
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
        Label distribution
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Frequency of primary emotion labels over the current time window.
      </Typography>
      <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 1 }}>
        {entries.map(([label, count]) => {
          const pct = (count / total) * 100;
          return (
            <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box sx={{ minWidth: 90 }}>
                <Typography variant="body2">{label}</Typography>
              </Box>
              <Box sx={{ flex: 1, borderRadius: 999, bgcolor: 'rgba(255,255,255,0.04)', overflow: 'hidden' }}>
                <Box
                  sx={{
                    width: `${pct}%`,
                    minWidth: pct > 0 ? 8 : 0,
                    bgcolor: 'rgba(184,161,234,0.7)',
                    height: 8,
                  }}
                />
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ minWidth: 60, textAlign: 'right' }}>
                {count} · {pct.toFixed(0)}%
              </Typography>
            </Box>
          );
        })}
        {entries.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No labeled emotion states in the selected window.
          </Typography>
        )}
      </Box>
    </Paper>
  );
};

export const EmotionPage: React.FC = () => {
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [history, setHistory] = React.useState<EmotionHistoryItemDto[]>([]);
  const [windowHours, setWindowHours] = React.useState<number>(24);

  React.useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        // For windows up to 72h use hours, beyond that switch to days for backend convenience.
        const query: { limit: number; hours?: number; days?: number } = { limit: 200 };
        if (windowHours <= 72) {
          query.hours = windowHours;
        } else {
          query.days = Math.round(windowHours / 24);
        }
        const response = await fetchEmotionHistory(query);
        if (!cancelled) {
          setHistory(response.history ?? []);
        }
      } catch (e) {
        if (!cancelled) {
          setError((e as Error).message ?? 'Failed to load emotion history');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [windowHours]);

  const marks = [
    { value: 1, label: '1h' },
    { value: 24, label: '24h' },
    { value: 72, label: '3d' },
    { value: 168, label: '7d' },
  ];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Page header with actions */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box />
        {!loading && !error && history.length > 0 && (
          <EmotionPageActions history={history} />
        )}
      </Box>
      
      {/* Lookback window slider */}
      <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1.5, maxWidth: 480, borderRadius: 1 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
          Lookback window
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Choose how far back to inspect emotional history.
        </Typography>
        <Slider
          size="small"
          value={windowHours}
          min={1}
          max={168}
          step={null}
          marks={marks}
          onChange={(_, value) => {
            if (typeof value === 'number') setWindowHours(value);
          }}
        />
      </Paper>

      {error && (
        <Alert severity="error" sx={{ maxWidth: 640 }}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Paper sx={{ p: 3, borderRadius: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 6 }}>
            <CircularProgress size={24} />
          </Box>
        </Paper>
      ) : history.length === 0 ? (
        <Paper sx={{ p: 3, borderRadius: 1 }}>
          <Typography variant="body1" color="text.secondary">
            No emotion history available yet. Once AICO is running and the emotion engine records states, this page
            will show the full emotion strip, circumplex, and label distribution.
          </Typography>
        </Paper>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          <EmotionStrip history={history} windowHours={windowHours} />
          <EmotionTimeSeries history={history} />
          <EmotionStatistics history={history} />
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'minmax(0, 3fr) minmax(0, 2fr)' }, gap: 3 }}>
            <EmotionCircumplex history={history} />
            <EmotionLabelDistribution history={history} />
          </Box>
          <EmotionEpisodes history={history} />
        </Box>
      )}
    </Box>
  );
};
