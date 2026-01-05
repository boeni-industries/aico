import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import { Settings as SettingsIcon, Users as PeopleIcon, Smartphone as DevicesIcon, Shield as SecurityIcon, Gauge as SpeedIcon } from 'lucide-react';

interface OperationsCardProps {
  activeUsers: number;
  activeSessions: number;
  onClick?: () => void;
}

export const OperationsCard: React.FC<OperationsCardProps> = ({
  activeUsers,
  activeSessions,
  onClick,
}) => {
  return (
    <Box
      onClick={onClick}
      sx={{
        p: 3,
        borderRadius: '20px',
        border: '1.5px solid',
        borderColor: 'divider',
        bgcolor: 'background.paper',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
        cursor: 'pointer',
        transition: 'all 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-4px)',
          boxShadow: '0 12px 32px rgba(0,0,0,0.12)',
          borderColor: 'primary.main',
        },
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box
            sx={{
              width: 40,
              height: 40,
              borderRadius: '12px',
              bgcolor: 'rgba(59, 130, 246, 0.12)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <SettingsIcon sx={{ color: '#3B82F6', fontSize: 24 }} />
          </Box>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1.1rem' }}>
              Operations
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
              System Management
            </Typography>
          </Box>
        </Box>
        <Chip
          label="LIVE"
          size="small"
          sx={{
            bgcolor: 'rgba(16, 185, 129, 0.12)',
            color: '#10B981',
            border: '1px solid',
            borderColor: 'rgba(16, 185, 129, 0.3)',
            fontWeight: 700,
            fontSize: '0.7rem',
            height: 24,
          }}
        />
      </Box>

      {/* Metrics Grid */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 2,
          mb: 2.5,
        }}
      >
        {/* Active Users */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <PeopleIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Active Users
            </Typography>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {activeUsers}
          </Typography>
        </Box>

        {/* Active Sessions */}
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <DevicesIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
              Live Sessions
            </Typography>
          </Box>
          <Typography variant="h5" sx={{ fontWeight: 700, color: 'text.primary' }}>
            {activeSessions}
          </Typography>
        </Box>
      </Box>

      {/* Footer Stats */}
      <Box
        sx={{
          display: 'flex',
          gap: 2,
          pt: 2.5,
          borderTop: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <Box
            sx={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: '#3B82F6',
              boxShadow: '0 0 8px #3B82F640',
            }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            User management
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          <SecurityIcon sx={{ fontSize: 14, color: '#10B981' }} />
          <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.7rem' }}>
            Session control
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};
