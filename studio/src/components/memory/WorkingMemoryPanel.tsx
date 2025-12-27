import React from 'react';
import { Box, Typography, LinearProgress, Paper, Chip } from '@mui/material';
import { AccessTime as TimeIcon, Delete as DeleteIcon } from '@mui/icons-material';

interface WorkingMemoryPanelProps {
  activeItems: number;
  capacity: number;
  ttlUtilization: number;
  evictionRate: number;
  recentActivity: Array<{
    id: string;
    timestamp: string;
    action: 'read' | 'write' | 'evict';
    key: string;
  }>;
}

export const WorkingMemoryPanel: React.FC<WorkingMemoryPanelProps> = ({
  activeItems,
  capacity,
  ttlUtilization,
  evictionRate,
  recentActivity,
}) => {
  const utilizationPercent = (activeItems / capacity) * 100;

  return (
    <Box>
      <Typography
        variant="subtitle2"
        sx={{
          fontWeight: 600,
          mb: 2,
          textTransform: 'uppercase',
          fontSize: '0.75rem',
          letterSpacing: '0.1em',
          color: 'text.secondary',
        }}
      >
        Working Memory (LMDB)
      </Typography>

      {/* Metrics Grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2, mb: 3 }}>
        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.2)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 0.5, display: 'block' }}>
            ACTIVE ITEMS
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#3B82F6' }}>
            {activeItems.toLocaleString()}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.65rem' }}>
            / {capacity.toLocaleString()} capacity
          </Typography>
        </Paper>

        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 0.5, display: 'block' }}>
            TTL UTILIZATION
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#F59E0B' }}>
            {ttlUtilization}%
          </Typography>
        </Paper>

        <Paper sx={{ p: 2, borderRadius: '12px', bgcolor: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 0.5, display: 'block' }}>
            EVICTION RATE
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#EF4444' }}>
            {evictionRate}/min
          </Typography>
        </Paper>
      </Box>

      {/* Utilization Bar */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            Memory Utilization
          </Typography>
          <Typography variant="caption" sx={{ fontWeight: 700, fontSize: '0.7rem' }}>
            {utilizationPercent.toFixed(1)}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={utilizationPercent}
          sx={{
            height: 8,
            borderRadius: 4,
            bgcolor: 'rgba(59, 130, 246, 0.12)',
            '& .MuiLinearProgress-bar': {
              bgcolor: utilizationPercent > 80 ? '#EF4444' : utilizationPercent > 60 ? '#F59E0B' : '#3B82F6',
              borderRadius: 4,
            },
          }}
        />
      </Box>

      {/* Recent Activity */}
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem', mb: 1.5, display: 'block' }}>
          RECENT ACTIVITY
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {recentActivity.slice(0, 5).map((activity) => (
            <Box
              key={activity.id}
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                p: 1.5,
                borderRadius: '8px',
                bgcolor: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid',
                borderColor: 'divider',
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                {activity.action === 'evict' ? (
                  <DeleteIcon sx={{ fontSize: 16, color: '#EF4444' }} />
                ) : (
                  <TimeIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                )}
                <Typography variant="body2" sx={{ fontSize: '0.8rem', fontFamily: 'monospace' }}>
                  {activity.key}
                </Typography>
              </Box>
              <Chip
                label={activity.action.toUpperCase()}
                size="small"
                sx={{
                  height: 20,
                  fontSize: '0.65rem',
                  fontWeight: 700,
                  bgcolor: activity.action === 'evict' ? 'rgba(239, 68, 68, 0.12)' : 'rgba(59, 130, 246, 0.12)',
                  color: activity.action === 'evict' ? '#EF4444' : '#3B82F6',
                  border: '1px solid',
                  borderColor: activity.action === 'evict' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(59, 130, 246, 0.3)',
                }}
              />
            </Box>
          ))}
        </Box>
      </Box>
    </Box>
  );
};
