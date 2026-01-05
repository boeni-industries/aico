import React from 'react';
import { Box, Typography, Paper, Chip } from '@mui/material';
import { CheckCircle as HealthyIcon, AlertTriangle as WarningIcon, TrendingUp as TrendingIcon } from 'lucide-react';

export const MessageBusPanel: React.FC = () => {
  // Mock data - replace with actual API calls
  const topics = [
    { name: 'conversation.events', rate: 145, backlog: 0, consumers: 3, health: 'healthy' },
    { name: 'memory.consolidation', rate: 23, backlog: 2, consumers: 2, health: 'healthy' },
    { name: 'agency.goals', rate: 8, backlog: 0, consumers: 1, health: 'healthy' },
    { name: 'scheduler.jobs', rate: 67, backlog: 12, consumers: 2, health: 'degraded' },
    { name: 'system.logs', rate: 234, backlog: 0, consumers: 4, health: 'healthy' },
  ];

  const totalRate = topics.reduce((sum, t) => sum + t.rate, 0);
  const totalBacklog = topics.reduce((sum, t) => sum + t.backlog, 0);

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
          Message Bus
        </Typography>
        <Chip
          label={totalBacklog === 0 ? 'HEALTHY' : 'BACKLOG'}
          size="small"
          sx={{
            bgcolor: totalBacklog === 0 ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
            color: totalBacklog === 0 ? '#10B981' : '#F59E0B',
            border: '1px solid',
            borderColor: totalBacklog === 0 ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)',
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
            Messages/sec
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 1 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#8DD6B8' }}>
              {totalRate}
            </Typography>
            <TrendingIcon sx={{ fontSize: 16, color: '#10B981' }} />
          </Box>
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', display: 'block', mb: 0.5 }}>
            Backlog
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: totalBacklog > 0 ? '#F59E0B' : '#10B981' }}>
            {totalBacklog}
          </Typography>
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', display: 'block', mb: 0.5 }}>
            Topics
          </Typography>
          <Typography variant="h5" sx={{ fontWeight: 700, color: '#B8A1EA' }}>
            {topics.length}
          </Typography>
        </Box>
      </Box>

      {/* Topics List */}
      <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', mb: 1, display: 'block' }}>
        ACTIVE TOPICS
      </Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, flex: 1, overflow: 'auto' }}>
        {topics.map((topic) => (
          <Box
            key={topic.name}
            sx={{
              p: 2,
              borderRadius: '12px',
              bgcolor: 'rgba(255,255,255,0.03)',
              border: '1px solid',
              borderColor: topic.health === 'healthy' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
              transition: 'all 0.2s',
              '&:hover': {
                bgcolor: 'rgba(141, 214, 184, 0.05)',
                borderColor: 'rgba(141, 214, 184, 0.4)',
              },
              cursor: 'pointer',
            }}
          >
            {/* Topic Header */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {topic.health === 'healthy' ? (
                  <HealthyIcon sx={{ fontSize: 16, color: '#10B981' }} />
                ) : (
                  <WarningIcon sx={{ fontSize: 16, color: '#F59E0B' }} />
                )}
                <Typography variant="caption" sx={{ fontSize: '0.8rem', fontWeight: 600, fontFamily: 'monospace' }}>
                  {topic.name}
                </Typography>
              </Box>
              <Chip
                label={`${topic.consumers} consumers`}
                size="small"
                sx={{
                  bgcolor: 'rgba(255,255,255,0.05)',
                  color: 'text.secondary',
                  fontSize: '0.6rem',
                  height: 18,
                  fontWeight: 500,
                }}
              />
            </Box>

            {/* Topic Metrics */}
            <Box sx={{ display: 'flex', gap: 3 }}>
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem', display: 'block' }}>
                  Rate
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600, fontSize: '0.85rem', color: '#8DD6B8' }}>
                  {topic.rate} msg/s
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.65rem', display: 'block' }}>
                  Backlog
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.85rem',
                    color: topic.backlog > 0 ? '#F59E0B' : '#10B981'
                  }}
                >
                  {topic.backlog}
                </Typography>
              </Box>
            </Box>
          </Box>
        ))}
      </Box>
    </Paper>
  );
};
