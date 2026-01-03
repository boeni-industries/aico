import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import {
  Refresh as RestartIcon,
  CloudUpload as DeployIcon,
  Error as ErrorIcon,
  CheckCircle as SuccessIcon,
  Schedule as JobIcon,
} from '@mui/icons-material';

export const OperationalTimeline: React.FC = () => {
  // Mock data - replace with actual API calls
  const events = [
    { id: 1, type: 'deploy', title: 'Backend v2.1.3 deployed', time: '2h ago', status: 'success' },
    { id: 2, type: 'restart', title: 'Modelservice restarted', time: '4h ago', status: 'success' },
    { id: 3, type: 'error', title: 'Gateway error spike detected', time: '6h ago', status: 'error' },
    { id: 4, type: 'job', title: 'Memory consolidation completed', time: '8h ago', status: 'success' },
    { id: 5, type: 'deploy', title: 'Studio v1.2.0 deployed', time: '12h ago', status: 'success' },
    { id: 6, type: 'restart', title: 'Scheduler restarted', time: '1d ago', status: 'success' },
  ];

  const eventConfig = {
    deploy: { icon: DeployIcon, color: '#8B5CF6', bg: 'rgba(139, 92, 246, 0.12)' },
    restart: { icon: RestartIcon, color: '#3B82F6', bg: 'rgba(59, 130, 246, 0.12)' },
    error: { icon: ErrorIcon, color: '#EF4444', bg: 'rgba(239, 68, 68, 0.12)' },
    job: { icon: JobIcon, color: '#10B981', bg: 'rgba(16, 185, 129, 0.12)' },
  };

  return (
    <Paper
      sx={{
        p: 3,
        borderRadius: '20px',
        bgcolor: 'rgba(255, 255, 255, 0.02)',
        backdropFilter: 'blur(12px)',
        border: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Typography
        variant="subtitle2"
        sx={{
          fontWeight: 600,
          textTransform: 'uppercase',
          fontSize: '0.75rem',
          letterSpacing: '0.1em',
          color: 'text.secondary',
          mb: 3,
        }}
      >
        Operational Timeline
      </Typography>

      {/* Timeline */}
      <Box sx={{ position: 'relative' }}>
        {/* Timeline Line */}
        <Box
          sx={{
            position: 'absolute',
            left: 16,
            top: 0,
            bottom: 0,
            width: 2,
            bgcolor: 'rgba(184, 161, 234, 0.2)',
          }}
        />

        {/* Events */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {events.map((event, index) => {
            const config = eventConfig[event.type as keyof typeof eventConfig];
            const EventIcon = config.icon;

            return (
              <Box
                key={event.id}
                sx={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 2,
                  position: 'relative',
                }}
              >
                {/* Timeline Dot */}
                <Box
                  sx={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    bgcolor: config.bg,
                    border: '2px solid',
                    borderColor: config.color,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    zIndex: 1,
                  }}
                >
                  <EventIcon sx={{ fontSize: 16, color: config.color }} />
                </Box>

                {/* Event Content */}
                <Box
                  sx={{
                    flex: 1,
                    p: 2,
                    borderRadius: '12px',
                    bgcolor: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    transition: 'all 0.2s',
                    '&:hover': {
                      bgcolor: 'rgba(184, 161, 234, 0.05)',
                      borderColor: 'rgba(184, 161, 234, 0.3)',
                    },
                    cursor: 'pointer',
                  }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.85rem' }}>
                      {event.title}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                        {event.time}
                      </Typography>
                      {event.status === 'success' && (
                        <SuccessIcon sx={{ fontSize: 14, color: '#10B981' }} />
                      )}
                      {event.status === 'error' && (
                        <ErrorIcon sx={{ fontSize: 14, color: '#EF4444' }} />
                      )}
                    </Box>
                  </Box>
                </Box>
              </Box>
            );
          })}
        </Box>
      </Box>
    </Paper>
  );
};
