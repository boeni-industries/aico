import React from 'react';
import { Box, Typography, Paper, Chip, LinearProgress } from '@mui/material';
import { Clock as ScheduleIcon, CheckCircle as SuccessIcon, AlertCircle as ErrorIcon, Pending as PendingIcon } from 'lucide-react';

export const SchedulerPanel: React.FC = () => {
  // Mock data - replace with actual API calls
  const queues = [
    { name: 'user_facing', jobs: 12, capacity: 50, color: '#3B82F6', priority: 'High' },
    { name: 'background_light', jobs: 34, capacity: 100, color: '#8B5CF6', priority: 'Medium' },
    { name: 'background_heavy', jobs: 8, capacity: 20, color: '#EC4899', priority: 'Medium' },
    { name: 'maintenance', jobs: 3, capacity: 10, color: '#F59E0B', priority: 'Low' },
  ];

  const recentJobs = [
    { id: 'job_1234', queue: 'user_facing', status: 'success', duration: '1.2s', time: '2m ago' },
    { id: 'job_1235', queue: 'background_light', status: 'success', duration: '3.4s', time: '3m ago' },
    { id: 'job_1236', queue: 'user_facing', status: 'failed', duration: '0.8s', time: '5m ago' },
    { id: 'job_1237', queue: 'maintenance', status: 'running', duration: '12.3s', time: 'now' },
    { id: 'job_1238', queue: 'background_heavy', status: 'success', duration: '45.2s', time: '8m ago' },
  ];

  const totalJobs = queues.reduce((sum, q) => sum + q.jobs, 0);
  const failedJobs = recentJobs.filter(j => j.status === 'failed').length;

  const statusConfig = {
    success: { icon: SuccessIcon, color: '#10B981', bg: 'rgba(16, 185, 129, 0.12)' },
    failed: { icon: ErrorIcon, color: '#EF4444', bg: 'rgba(239, 68, 68, 0.12)' },
    running: { icon: PendingIcon, color: '#3B82F6', bg: 'rgba(59, 130, 246, 0.12)' },
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
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography
          variant="subtitle2"
          sx={{
            fontWeight: 600,
            textTransform: 'uppercase',
            fontSize: '0.75rem',
            letterSpacing: '0.1em',
            color: 'text.secondary',
          }}
        >
          Scheduler & Jobs
        </Typography>
        <Chip
          icon={<ScheduleIcon sx={{ fontSize: 14 }} />}
          label={`${totalJobs} Active`}
          size="small"
          sx={{
            bgcolor: 'rgba(184, 161, 234, 0.15)',
            color: '#B8A1EA',
            fontWeight: 700,
            fontSize: '0.7rem',
            height: 24,
          }}
        />
      </Box>

      {/* KPIs */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', display: 'block', mb: 0.5 }}>
            Jobs Today
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#B8A1EA' }}>
            1,247
          </Typography>
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', display: 'block', mb: 0.5 }}>
            Failed
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: failedJobs > 0 ? '#EF4444' : '#10B981' }}>
            {failedJobs}
          </Typography>
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', display: 'block', mb: 0.5 }}>
            Success Rate
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#10B981' }}>
            99.2%
          </Typography>
        </Box>
      </Box>

      {/* Queue Status */}
      <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', mb: 2, display: 'block' }}>
        QUEUE STATUS
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
        {queues.map((queue) => {
          const utilization = (queue.jobs / queue.capacity) * 100;
          return (
            <Box key={queue.name}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      bgcolor: queue.color,
                    }}
                  />
                  <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 600, fontFamily: 'monospace' }}>
                    {queue.name}
                  </Typography>
                  <Chip
                    label={queue.priority}
                    size="small"
                    sx={{
                      bgcolor: 'rgba(255,255,255,0.05)',
                      color: 'text.secondary',
                      fontSize: '0.6rem',
                      height: 16,
                      fontWeight: 500,
                    }}
                  />
                </Box>
                <Typography variant="caption" sx={{ fontSize: '0.7rem', color: 'text.secondary' }}>
                  {queue.jobs}/{queue.capacity}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={utilization}
                sx={{
                  height: 6,
                  borderRadius: 3,
                  bgcolor: 'rgba(255,255,255,0.05)',
                  '& .MuiLinearProgress-bar': {
                    bgcolor: queue.color,
                    borderRadius: 3,
                  },
                }}
              />
            </Box>
          );
        })}
      </Box>

      {/* Recent Jobs */}
      <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', mb: 1, display: 'block' }}>
        RECENT JOBS
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, flex: 1, overflow: 'auto' }}>
        {recentJobs.map((job) => {
          const config = statusConfig[job.status as keyof typeof statusConfig];
          const StatusIcon = config.icon;
          return (
            <Box
              key={job.id}
              sx={{
                p: 1.5,
                borderRadius: '12px',
                bgcolor: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
                display: 'flex',
                alignItems: 'center',
                gap: 1.5,
                transition: 'all 0.2s',
                '&:hover': {
                  bgcolor: 'rgba(184, 161, 234, 0.05)',
                  borderColor: 'rgba(184, 161, 234, 0.3)',
                },
                cursor: 'pointer',
              }}
            >
              <Box
                sx={{
                  width: 28,
                  height: 28,
                  borderRadius: '8px',
                  bgcolor: config.bg,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <StatusIcon sx={{ fontSize: 14, color: config.color }} />
              </Box>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="caption" sx={{ fontSize: '0.7rem', fontWeight: 600, fontFamily: 'monospace', display: 'block' }}>
                  {job.id}
                </Typography>
                <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>
                  {job.queue} • {job.duration}
                </Typography>
              </Box>
              <Typography variant="caption" sx={{ fontSize: '0.65rem', color: 'text.secondary' }}>
                {job.time}
              </Typography>
            </Box>
          );
        })}
      </Box>
    </Paper>
  );
};
