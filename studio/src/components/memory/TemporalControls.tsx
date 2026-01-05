import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Box, IconButton, Typography, Slider, Fade, Tooltip } from '@mui/material';
import { Play, Pause, SkipBack, SkipForward, Rewind, FastForward, Circle } from 'lucide-react';

interface TemporalControlsProps {
  onTimeChange: (timestamp: string, isLive: boolean) => void;
  activityData?: Array<{ date: string; changeCount: number }>;
  isLoading?: boolean;
}

export const TemporalControls: React.FC<TemporalControlsProps> = ({
  onTimeChange,
  activityData = [],
  isLoading = false
}) => {
  // Use refs for time boundaries to avoid stale closures
  const nowRef = useRef(new Date());
  const oneYearAgoRef = useRef((() => {
    const date = new Date();
    date.setFullYear(date.getFullYear() - 1);
    return date;
  })());
  
  const [isLive, setIsLive] = useState(true);
  const [selectedTime, setSelectedTime] = useState<Date>(() => new Date());
  const [isPlaying, setIsPlaying] = useState(false);
  const [sliderValue, setSliderValue] = useState(100);
  const [isHovered, setIsHovered] = useState(false);
  
  const debounceTimerRef = useRef<NodeJS.Timeout | undefined>(undefined);
  
  // Update now reference periodically to keep it fresh
  useEffect(() => {
    const interval = setInterval(() => {
      nowRef.current = new Date();
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Convert slider value (0-100) to date
  const sliderToDate = useCallback((value: number): Date => {
    const now = nowRef.current;
    const oneYearAgo = oneYearAgoRef.current;
    const range = now.getTime() - oneYearAgo.getTime();
    const position = (value / 100) * range;
    return new Date(oneYearAgo.getTime() + position);
  }, []);

  // Convert date to slider value
  const dateToSlider = useCallback((date: Date): number => {
    const now = nowRef.current;
    const oneYearAgo = oneYearAgoRef.current;
    const range = now.getTime() - oneYearAgo.getTime();
    const position = date.getTime() - oneYearAgo.getTime();
    return (position / range) * 100;
  }, []);

  // Handle slider change with debouncing
  const handleSliderChange = useCallback((_event: Event, value: number | number[]) => {
    const val = Array.isArray(value) ? value[0] : value;
    setSliderValue(val);
    
    const newDate = sliderToDate(val);
    setSelectedTime(newDate);
    
    // Don't update isLive during drag - only on commit
    // This prevents control jitter while dragging

    // Debounce API calls
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    
    debounceTimerRef.current = setTimeout(() => {
      const finalIsLive = val >= 99.5; // Within 0.5% of end = live
      setIsLive(finalIsLive);
      onTimeChange(newDate.toISOString(), finalIsLive);
    }, 300);
  }, [sliderToDate, onTimeChange]);

  // Jump to live
  const goLive = useCallback(() => {
    const now = new Date();
    nowRef.current = now;
    setSliderValue(100);
    setSelectedTime(now);
    setIsLive(true);
    setIsPlaying(false);
    onTimeChange(now.toISOString(), true);
  }, [onTimeChange]);

  // Step time
  const stepTime = useCallback((days: number) => {
    const now = nowRef.current;
    const oneYearAgo = oneYearAgoRef.current;
    
    // Use functional state update to get current value and avoid stale closure
    setSelectedTime(currentTime => {
      // Use setDate() to properly handle calendar days, DST, and timezone transitions
      const newDate = new Date(currentTime);
      newDate.setDate(newDate.getDate() + days);
      
      // Clamp to valid range
      if (newDate < oneYearAgo) {
        newDate.setTime(oneYearAgo.getTime());
      } else if (newDate > now) {
        newDate.setTime(now.getTime());
      }
      
      const newValue = dateToSlider(newDate);
      
      // Check if we're within 1 second of NOW (not using slider threshold)
      const timeDiffMs = Math.abs(now.getTime() - newDate.getTime());
      const newIsLive = timeDiffMs < 1000;
      
      setSliderValue(newValue);
      setIsLive(newIsLive);
      
      // Defer callback to next tick to avoid render-time state updates
      setTimeout(() => {
        onTimeChange(newDate.toISOString(), newIsLive);
      }, 0);
      
      return newDate;
    });
  }, [dateToSlider, onTimeChange]);

  // Play animation
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setSelectedTime(prev => {
        const now = nowRef.current;
        // Use setDate() for proper calendar day handling
        const newDate = new Date(prev);
        newDate.setDate(newDate.getDate() + 1);
        
        if (newDate >= now) {
          setIsPlaying(false);
          goLive();
          return now;
        }
        const newValue = dateToSlider(newDate);
        setSliderValue(newValue);
        onTimeChange(newDate.toISOString(), false);
        return newDate;
      });
    }, 100);

    return () => clearInterval(interval);
  }, [isPlaying, dateToSlider, onTimeChange, goLive]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          stepTime(e.shiftKey ? -30 : -1);
          break;
        case 'ArrowRight':
          e.preventDefault();
          stepTime(e.shiftKey ? 30 : 1);
          break;
        case ' ':
          e.preventDefault();
          if (isLive) return;
          setIsPlaying(prev => !prev);
          break;
        case 'l':
        case 'L':
          e.preventDefault();
          goLive();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [stepTime, isLive, goLive]);

  // Calculate activity heatmap
  const heatmapBars = useMemo(() => {
    if (!activityData.length) return [];

    const bars = 100;
    const now = nowRef.current;
    const oneYearAgo = oneYearAgoRef.current;
    const range = now.getTime() - oneYearAgo.getTime();
    const barWidth = range / bars;

    const barData = Array(bars).fill(0);
    
    activityData.forEach(activity => {
      const activityTime = new Date(activity.date).getTime();
      const barIndex = Math.floor((activityTime - oneYearAgo.getTime()) / barWidth);
      if (barIndex >= 0 && barIndex < bars) {
        barData[barIndex] += activity.changeCount;
      }
    });

    const maxActivity = Math.max(...barData, 1);
    return barData.map(count => count / maxActivity);
  }, [activityData]);

  // Format date
  const formatDate = useCallback((date: Date): string => {
    const now = nowRef.current;
    const options: Intl.DateTimeFormatOptions = { 
      month: 'short', 
      day: 'numeric',
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    };
    return date.toLocaleDateString(undefined, options);
  }, []);

  return (
    <Fade in={true} timeout={500}>
      <Box
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        sx={{
          position: 'absolute',
          bottom: 24,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 100,
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          opacity: isHovered || !isLive || isPlaying ? 1 : 0.7,
          '&:hover': {
            transform: 'translateX(-50%) translateY(-4px)',
          }
        }}
      >
        {/* Main control bar */}
        <Box sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          px: 3,
          py: 1.5,
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
          backdropFilter: 'blur(20px) saturate(180%)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '16px',
          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.4), inset 0 1px 0 0 rgba(255, 255, 255, 0.1)',
          minWidth: 600,
          maxWidth: 800,
        }}>
          {/* VCR Controls */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Tooltip title="Back 1 Month (Shift+←)" placement="top">
              <span>
                <IconButton
                  size="small"
                  onClick={() => stepTime(-30)}
                  disabled={selectedTime <= oneYearAgoRef.current}
                  sx={{
                    color: 'rgba(255,255,255,0.7)',
                    '&:hover': { color: '#3B82F6', bgcolor: 'rgba(59, 130, 246, 0.1)' },
                    '&:disabled': { color: 'rgba(255,255,255,0.2)' }
                  }}
                >
                  <Rewind size={20} />
                </IconButton>
              </span>
            </Tooltip>

            <Tooltip title="Previous Day (←)" placement="top">
              <span>
                <IconButton
                  size="small"
                  onClick={() => stepTime(-1)}
                  disabled={selectedTime <= oneYearAgoRef.current}
                  sx={{
                    color: 'rgba(255,255,255,0.7)',
                    '&:hover': { color: '#3B82F6', bgcolor: 'rgba(59, 130, 246, 0.1)' },
                    '&:disabled': { color: 'rgba(255,255,255,0.2)' }
                  }}
                >
                  <SkipBack size={20} />
                </IconButton>
              </span>
            </Tooltip>

            <Tooltip title={isPlaying ? "Pause (Space)" : "Play (Space)"} placement="top">
              <span>
                <IconButton
                  size="small"
                  onClick={() => setIsPlaying(!isPlaying)}
                  disabled={isLive}
                  sx={{
                    color: isPlaying ? '#10B981' : 'rgba(255,255,255,0.7)',
                    bgcolor: isPlaying ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
                    '&:hover': { 
                      color: '#10B981', 
                      bgcolor: 'rgba(16, 185, 129, 0.2)' 
                    },
                    '&:disabled': { color: 'rgba(255,255,255,0.2)' }
                  }}
                >
                  {isPlaying ? <Pause size={22} /> : <Play size={22} />}
                </IconButton>
              </span>
            </Tooltip>

            <Tooltip title="Next Day (→)" placement="top">
              <span>
                <IconButton
                  size="small"
                  onClick={() => stepTime(1)}
                  disabled={isLive}
                  sx={{
                    color: 'rgba(255,255,255,0.7)',
                    '&:hover': { color: '#3B82F6', bgcolor: 'rgba(59, 130, 246, 0.1)' },
                    '&:disabled': { color: 'rgba(255,255,255,0.2)' }
                  }}
                >
                  <SkipForward size={20} />
                </IconButton>
              </span>
            </Tooltip>

            <Tooltip title="Forward 1 Month (Shift+→)" placement="top">
              <span>
                <IconButton
                  size="small"
                  onClick={() => stepTime(30)}
                  disabled={isLive}
                  sx={{
                    color: 'rgba(255,255,255,0.7)',
                    '&:hover': { color: '#3B82F6', bgcolor: 'rgba(59, 130, 246, 0.1)' },
                    '&:disabled': { color: 'rgba(255,255,255,0.2)' }
                  }}
                >
                  <FastForward size={20} />
                </IconButton>
              </span>
            </Tooltip>
          </Box>

          {/* Timeline slider */}
          <Box sx={{ flex: 1, position: 'relative', px: 2 }}>
            {/* Activity heatmap background */}
            {heatmapBars.length > 0 && (
              <Box sx={{
                position: 'absolute',
                bottom: 8,
                left: 16,
                right: 16,
                display: 'flex',
                alignItems: 'flex-end',
                height: 20,
                gap: '1px',
                pointerEvents: 'none'
              }}>
                {heatmapBars.map((intensity, index) => (
                  <Box
                    key={index}
                    sx={{
                      flex: 1,
                      height: `${Math.max(intensity * 100, 5)}%`,
                      bgcolor: intensity > 0
                        ? `rgba(59, 130, 246, ${0.2 + intensity * 0.5})`
                        : 'rgba(255,255,255,0.03)',
                      borderRadius: '1px',
                      transition: 'all 0.2s ease'
                    }}
                  />
                ))}
              </Box>
            )}

            <Slider
              value={sliderValue}
              onChange={handleSliderChange}
              min={0}
              max={100}
              step={0.1}
              disabled={isLoading}
              sx={{
                color: isLive ? '#10B981' : '#3B82F6',
                height: 6,
                '& .MuiSlider-thumb': {
                  width: 14,
                  height: 14,
                  bgcolor: isLive ? '#10B981' : '#3B82F6',
                  border: `2px solid ${isLive ? 'rgba(16, 185, 129, 0.3)' : 'rgba(59, 130, 246, 0.3)'}`,
                  boxShadow: isLive 
                    ? '0 0 12px rgba(16, 185, 129, 0.6)'
                    : '0 0 12px rgba(59, 130, 246, 0.6)',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    boxShadow: isLive
                      ? '0 0 16px rgba(16, 185, 129, 0.8)'
                      : '0 0 16px rgba(59, 130, 246, 0.8)',
                  }
                },
                '& .MuiSlider-track': {
                  background: isLive
                    ? 'linear-gradient(90deg, rgba(59, 130, 246, 0.5) 0%, rgba(16, 185, 129, 0.7) 100%)'
                    : 'linear-gradient(90deg, rgba(59, 130, 246, 0.5) 0%, rgba(59, 130, 246, 0.7) 100%)',
                  border: 'none',
                  height: 6
                },
                '& .MuiSlider-rail': {
                  bgcolor: 'rgba(255,255,255,0.08)',
                  height: 6
                }
              }}
            />
          </Box>

          {/* Date display and live button */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography
              variant="body2"
              sx={{
                minWidth: 100,
                textAlign: 'center',
                color: isLive ? '#10B981' : '#3B82F6',
                fontWeight: 600,
                fontSize: '0.875rem',
                fontVariantNumeric: 'tabular-nums'
              }}
            >
              {isLive ? 'NOW' : formatDate(selectedTime)}
            </Typography>

            {!isLive && (
              <Tooltip title="Go Live (L)" placement="top">
                <IconButton
                  size="small"
                  onClick={goLive}
                  sx={{
                    color: '#10B981',
                    bgcolor: 'rgba(16, 185, 129, 0.15)',
                    '&:hover': {
                      bgcolor: 'rgba(16, 185, 129, 0.25)',
                      transform: 'scale(1.05)'
                    },
                    transition: 'all 0.2s ease'
                  }}
                >
                  <Circle size={16} />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Box>

      </Box>
    </Fade>
  );
};
