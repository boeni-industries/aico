import React from 'react';
import { Box, Paper, Typography, Chip } from '@mui/material';
import { formatDistanceToNow } from 'date-fns';
import { Circle as CircleIcon, CheckCircle as CheckCircleIcon, PauseCircle as PauseCircleIcon, PlusCircle as AddCircleIcon } from 'lucide-react';

interface ActivityEvent {
  id: string;
  timestamp: string;
  type: 'goal_created' | 'goal_activated' | 'goal_paused' | 'goal_completed';
  title: string;
  description?: string;
  origin?: string;
}

interface RecentActivityProps {
  events?: ActivityEvent[];
  loading?: boolean;
}

const eventIcons = {
  goal_created: <AddCircleIcon sx={{ fontSize: 16 }} />,
  goal_activated: <CircleIcon sx={{ fontSize: 16 }} />,
  goal_paused: <PauseCircleIcon sx={{ fontSize: 16 }} />,
  goal_completed: <CheckCircleIcon sx={{ fontSize: 16 }} />,
};

const eventColors = {
  goal_created: { bg: 'rgba(59, 130, 246, 0.12)', text: '#3B82F6', border: 'rgba(59, 130, 246, 0.3)' },
  goal_activated: { bg: 'rgba(16, 185, 129, 0.12)', text: '#10B981', border: 'rgba(16, 185, 129, 0.3)' },
  goal_paused: { bg: 'rgba(245, 158, 11, 0.12)', text: '#F59E0B', border: 'rgba(245, 158, 11, 0.3)' },
  goal_completed: { bg: 'rgba(107, 114, 128, 0.12)', text: '#6B7280', border: 'rgba(107, 114, 128, 0.3)' },
};

const eventLabels = {
  goal_created: 'Created',
  goal_activated: 'Activated',
  goal_paused: 'Paused',
  goal_completed: 'Completed',
};

export const RecentActivity: React.FC<RecentActivityProps> = ({ events = [], loading }) => {
  if (loading) {
    return (
      <Typography variant="body2" color="text.secondary">
        Loading activity...
      </Typography>
    );
  }

  if (events.length === 0) {
    return (
      <Paper
        sx={{
          p: 4,
          borderRadius: '20px',
          border: '1.5px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
          backdropFilter: 'blur(12px)',
          textAlign: 'center',
        }}
      >
        <Typography variant="body2" color="text.secondary">
          No recent activity in the last 24 hours
        </Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ position: 'relative' }}>
      {/* Timeline line */}
      <Box
        sx={{
          position: 'absolute',
          left: 19,
          top: 24,
          bottom: 24,
          width: 2,
          bgcolor: 'divider',
          opacity: 0.3,
        }}
      />

      {/* Events */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {events.map((event, index) => {
          const colors = eventColors[event.type];
          let timeAgo = 'Unknown time';
          try {
            timeAgo = formatDistanceToNow(new Date(event.timestamp), { addSuffix: true });
          } catch {
            // Keep default 'Unknown time'
          }

          return (
            <Box key={event.id} sx={{ display: 'flex', gap: 2, position: 'relative' }}>
              {/* Timeline dot */}
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: '12px',
                  bgcolor: colors.bg,
                  border: '1.5px solid',
                  borderColor: colors.border,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: colors.text,
                  flexShrink: 0,
                  zIndex: 1,
                  backdropFilter: 'blur(8px)',
                }}
              >
                {eventIcons[event.type]}
              </Box>

              {/* Event card */}
              <Paper
                sx={{
                  flexGrow: 1,
                  p: 2.5,
                  borderRadius: '16px',
                  border: '1.5px solid',
                  borderColor: 'divider',
                  bgcolor: 'background.paper',
                  backdropFilter: 'blur(12px)',
                  boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    transform: 'translateX(4px)',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
                    borderColor: colors.border,
                  },
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Chip
                      label={eventLabels[event.type]}
                      size="small"
                      sx={{
                        bgcolor: colors.bg,
                        color: colors.text,
                        border: '1px solid',
                        borderColor: colors.border,
                        fontWeight: 600,
                        fontSize: '0.7rem',
                        height: 22,
                      }}
                    />
                    {event.origin && (
                      <Chip
                        label={event.origin}
                        size="small"
                        sx={{
                          bgcolor: 'background.default',
                          fontSize: '0.7rem',
                          height: 22,
                        }}
                      />
                    )}
                  </Box>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ fontSize: '0.7rem', fontFamily: 'monospace' }}
                  >
                    {timeAgo}
                  </Typography>
                </Box>

                <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.95rem', mb: 0.5 }}>
                  {event.title}
                </Typography>

                {event.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.85rem', lineHeight: 1.5 }}>
                    {event.description}
                  </Typography>
                )}
              </Paper>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};
