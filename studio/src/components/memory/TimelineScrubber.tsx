import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Box, Typography, Slider, IconButton, ButtonGroup, Button, Tooltip } from '@mui/material';
import { Play, Pause, SkipBack, SkipForward } from 'lucide-react';

interface TimelineScrubberProps {
  onTimeChange: (timestamp: string) => void;
  activityData?: Array<{ date: string; changeCount: number }>;
  minDate?: Date;
  maxDate?: Date;
  currentTime?: Date;
}

export const TimelineScrubber: React.FC<TimelineScrubberProps> = ({
  onTimeChange,
  activityData = [],
  minDate,
  maxDate,
  currentTime
}) => {
  const now = useMemo(() => new Date(), []);
  const startDate = minDate || new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000); // 1 year ago
  const endDate = maxDate || now;
  
  const [selectedTime, setSelectedTime] = useState<Date>(currentTime || now);
  const [isPlaying, setIsPlaying] = useState(false);
  const [sliderValue, setSliderValue] = useState(100); // 0-100 representing timeline position

  // Convert date to slider value (0-100)
  const dateToSliderValue = useCallback((date: Date): number => {
    const totalRange = endDate.getTime() - startDate.getTime();
    const currentPosition = date.getTime() - startDate.getTime();
    return (currentPosition / totalRange) * 100;
  }, [startDate, endDate]);

  // Convert slider value to date
  const sliderValueToDate = useCallback((value: number): Date => {
    const totalRange = endDate.getTime() - startDate.getTime();
    const position = (value / 100) * totalRange;
    return new Date(startDate.getTime() + position);
  }, [startDate, endDate]);

  // Update slider when selectedTime changes
  useEffect(() => {
    setSliderValue(dateToSliderValue(selectedTime));
  }, [selectedTime, dateToSliderValue]);

  // Handle slider change
  const handleSliderChange = useCallback((_event: Event, newValue: number | number[]) => {
    const value = Array.isArray(newValue) ? newValue[0] : newValue;
    setSliderValue(value);
    const newDate = sliderValueToDate(value);
    setSelectedTime(newDate);
  }, [sliderValueToDate]);

  // Handle slider commit (when user releases)
  const handleSliderCommit = useCallback((_event: React.SyntheticEvent | Event, newValue: number | number[]) => {
    const value = Array.isArray(newValue) ? newValue[0] : newValue;
    const newDate = sliderValueToDate(value);
    onTimeChange(newDate.toISOString());
  }, [sliderValueToDate, onTimeChange]);

  // Preset time jumps
  const jumpToPreset = useCallback((daysAgo: number) => {
    const targetDate = daysAgo === 0 ? now : new Date(now.getTime() - daysAgo * 24 * 60 * 60 * 1000);
    setSelectedTime(targetDate);
    onTimeChange(targetDate.toISOString());
  }, [now, onTimeChange]);

  // Step forward/backward
  const stepTime = useCallback((days: number) => {
    const newDate = new Date(selectedTime.getTime() + days * 24 * 60 * 60 * 1000);
    if (newDate >= startDate && newDate <= endDate) {
      setSelectedTime(newDate);
      onTimeChange(newDate.toISOString());
    }
  }, [selectedTime, startDate, endDate, onTimeChange]);

  // Play/pause animation
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setSelectedTime(prev => {
        const newDate = new Date(prev.getTime() + 24 * 60 * 60 * 1000); // 1 day forward
        if (newDate >= endDate) {
          setIsPlaying(false);
          return endDate;
        }
        onTimeChange(newDate.toISOString());
        return newDate;
      });
    }, 100); // 100ms per day = ~3 seconds per month

    return () => clearInterval(interval);
  }, [isPlaying, endDate, onTimeChange]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          stepTime(e.shiftKey ? -30 : -1); // Shift = 1 month, normal = 1 day
          break;
        case 'ArrowRight':
          e.preventDefault();
          stepTime(e.shiftKey ? 30 : 1);
          break;
        case ' ':
          e.preventDefault();
          setIsPlaying(prev => !prev);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [stepTime]);

  // Calculate activity heatmap
  const heatmapBars = useMemo(() => {
    if (!activityData.length) return [];

    const bars = 60; // Number of bars in heatmap
    const timeRange = endDate.getTime() - startDate.getTime();
    const barWidth = timeRange / bars;

    const barData = Array(bars).fill(0);
    
    activityData.forEach(activity => {
      const activityTime = new Date(activity.date).getTime();
      const barIndex = Math.floor((activityTime - startDate.getTime()) / barWidth);
      if (barIndex >= 0 && barIndex < bars) {
        barData[barIndex] += activity.changeCount;
      }
    });

    const maxActivity = Math.max(...barData, 1);
    return barData.map(count => count / maxActivity);
  }, [activityData, startDate, endDate]);

  // Format date display
  const formatDate = (date: Date): string => {
    const isToday = date.toDateString() === now.toDateString();
    if (isToday) return 'NOW';
    
    const options: Intl.DateTimeFormatOptions = { 
      month: 'short', 
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    };
    return date.toLocaleDateString(undefined, options);
  };

  return (
    <Box sx={{
      width: '100%',
      p: 1,
      background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.9) 100%)',
      backdropFilter: 'blur(10px)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: '8px'
    }}>
      {/* Single compact row */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
        {/* Playback controls */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <IconButton 
            size="small" 
            onClick={() => stepTime(-1)}
            disabled={selectedTime <= startDate}
            sx={{ 
              p: 0.5,
              color: 'rgba(255,255,255,0.5)',
              '&:hover': { color: '#3B82F6' }
            }}
          >
            <SkipPrevious sx={{ fontSize: 18 }} />
          </IconButton>

          <IconButton 
            size="small" 
            onClick={() => setIsPlaying(!isPlaying)}
            sx={{ 
              p: 0.5,
              color: isPlaying ? '#10B981' : 'rgba(255,255,255,0.5)',
              '&:hover': { color: '#10B981' }
            }}
          >
            {isPlaying ? <Pause sx={{ fontSize: 18 }} /> : <PlayArrow sx={{ fontSize: 18 }} />}
          </IconButton>

          <IconButton 
            size="small" 
            onClick={() => stepTime(1)}
            disabled={selectedTime >= endDate}
            sx={{ 
              p: 0.5,
              color: 'rgba(255,255,255,0.5)',
              '&:hover': { color: '#3B82F6' }
            }}
          >
            <SkipNext sx={{ fontSize: 18 }} />
          </IconButton>
        </Box>

        {/* Date display */}
        <Typography variant="caption" sx={{ 
          minWidth: 80,
          color: selectedTime.toDateString() === now.toDateString() ? '#10B981' : '#3B82F6',
          fontWeight: 600,
          fontSize: '0.75rem'
        }}>
          {formatDate(selectedTime)}
        </Typography>

        {/* Timeline slider with inline heatmap */}
        <Box sx={{ flex: 1, position: 'relative' }}>
          {/* Activity heatmap as background */}
          {heatmapBars.length > 0 && (
            <Box sx={{ 
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              display: 'flex', 
              alignItems: 'flex-end', 
              height: '16px',
              gap: '1px',
              pointerEvents: 'none'
            }}>
              {heatmapBars.map((intensity, index) => (
                <Box
                  key={index}
                  sx={{
                    flex: 1,
                    height: `${Math.max(intensity * 100, 10)}%`,
                    bgcolor: intensity > 0 
                      ? `rgba(59, 130, 246, ${0.2 + intensity * 0.4})`
                      : 'rgba(255,255,255,0.03)',
                    borderRadius: '1px'
                  }}
                />
              ))}
            </Box>
          )}
          
          <Slider
            value={sliderValue}
            onChange={handleSliderChange}
            onChangeCommitted={handleSliderCommit}
            min={0}
            max={100}
            step={0.1}
            sx={{
              color: '#3B82F6',
              height: 4,
              '& .MuiSlider-thumb': {
                width: 12,
                height: 12,
                bgcolor: '#3B82F6',
                border: '2px solid rgba(59, 130, 246, 0.3)',
                boxShadow: '0 0 8px rgba(59, 130, 246, 0.6)',
                '&:hover': {
                  boxShadow: '0 0 12px rgba(59, 130, 246, 0.8)',
                }
              },
              '& .MuiSlider-track': {
                background: 'linear-gradient(90deg, rgba(59, 130, 246, 0.4) 0%, rgba(59, 130, 246, 0.7) 100%)',
                border: 'none',
                height: 4
              },
              '& .MuiSlider-rail': {
                bgcolor: 'transparent',
                height: 4
              }
            }}
          />
        </Box>

        {/* Preset buttons - compact */}
        <ButtonGroup size="small" variant="text" sx={{ 
          '& .MuiButton-root': {
            color: 'rgba(255,255,255,0.5)',
            fontSize: '0.65rem',
            textTransform: 'none',
            px: 0.75,
            py: 0.25,
            minWidth: 'auto',
            border: 'none',
            '&:hover': {
              color: '#3B82F6',
              bgcolor: 'rgba(59, 130, 246, 0.1)'
            }
          }
        }}>
          <Button onClick={() => jumpToPreset(7)}>1w</Button>
          <Button onClick={() => jumpToPreset(30)}>1m</Button>
          <Button onClick={() => jumpToPreset(180)}>6m</Button>
          <Button onClick={() => jumpToPreset(365)}>1y</Button>
          <Button onClick={() => jumpToPreset(0)}>Now</Button>
        </ButtonGroup>
      </Box>
    </Box>
  );
};
